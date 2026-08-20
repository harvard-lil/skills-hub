"""Pytest plugin for skill evaluation.

Automatically discovers rubric.yaml files in a skills/ directory,
provides fixtures for OpenAI clients and model configs, and
parametrizes tests over discovered scenarios.

This module is registered as a pytest plugin via the [project.entry-points.pytest11]
entry point, so it activates automatically when skill-eval is installed.
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path

import pytest
import yaml
from dotenv import load_dotenv

from .runner import ModelConfig, load_skill_as_system_prompt
from .trace_writer import rebuild_index

# The project root is discovered by walking up from CWD looking for hub.yaml or skills/
_PROJECT_ROOT: Path | None = None


def _find_project_root() -> Path:
    """Walk up from CWD to find a directory with hub.yaml or skills/."""
    cwd = Path.cwd()
    for candidate in [cwd, *cwd.parents]:
        if (candidate / "hub.yaml").exists() or (candidate / "skills").is_dir():
            return candidate
    return cwd


def _get_project_root() -> Path:
    global _PROJECT_ROOT
    if _PROJECT_ROOT is None:
        _PROJECT_ROOT = _find_project_root()
    return _PROJECT_ROOT


def pytest_addoption(parser):
    parser.addoption(
        "--rerun", action="store_true", default=False,
        help="Re-run scenarios even if a trace already exists.",
    )
    parser.addoption(
        "--skills-dir",
        default=None,
        help="Path to skills directory (defaults to skills/ in project root).",
    )


def pytest_configure(config):
    """Set up logging for the eval harness."""
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(name)s | %(message)s"))
    harness_logger = logging.getLogger("skill_eval")
    harness_logger.addHandler(handler)
    harness_logger.setLevel(logging.DEBUG if config.option.verbose > 1 else logging.INFO)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def pytest_sessionfinish(session, exitstatus):
    """Rebuild the trace index after all tests complete."""
    # With pytest-xdist, only the controller rebuilds
    if hasattr(session.config, "workerinput"):
        return
    traces_dir = _get_project_root() / "traces"
    if traces_dir.is_dir():
        rebuild_index(traces_dir)


def _extract_version(skill_path: Path) -> str:
    """Pull the version from SKILL.md YAML frontmatter."""
    text = skill_path.read_text(encoding="utf-8")
    m = re.search(r"version:\s*(.+)", text)
    return m.group(1).strip() if m else "0.0.0"


def _infer_group(skill_path: Path, skills_dir: Path) -> str:
    """Infer the group name from the path (first directory under skills/)."""
    try:
        rel = skill_path.relative_to(skills_dir)
        return rel.parts[0] if len(rel.parts) > 1 else "default"
    except ValueError:
        return "default"


def discover_rubrics(skills_dir: Path) -> list[dict]:
    """Find all rubric.yaml files and pair them with their SKILL.md."""
    rubrics = []
    for rubric_path in sorted(skills_dir.rglob("rubric.yaml")):
        skill_md = rubric_path.parent / "SKILL.md"
        if not skill_md.exists():
            continue
        with open(rubric_path, encoding="utf-8") as f:
            rubric = yaml.safe_load(f)
        rubric["_rubric_path"] = rubric_path
        rubric["_skill_path"] = skill_md
        rubric["_version"] = _extract_version(skill_md)
        rubric["_group"] = rubric.get("group", _infer_group(skill_md, skills_dir))
        rubrics.append(rubric)
    return rubrics


def _load_eval_config(project_root: Path) -> dict:
    """Load eval config from eval.yaml or tests/test_config.yaml."""
    for candidate in [
        project_root / "eval.yaml",
        project_root / "tests" / "test_config.yaml",
    ]:
        if candidate.exists():
            with open(candidate, encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
    return {}


@pytest.fixture(scope="session")
def eval_config() -> dict:
    return _load_eval_config(_get_project_root())


@pytest.fixture(scope="session")
def openai_client(eval_config) -> "OpenAI":
    from openai import OpenAI

    project_root = _get_project_root()
    load_dotenv(project_root / ".env")

    api_config = eval_config.get("api", {})
    api_key = os.environ.get(api_config.get("api_key_env", "OPENROUTER_API_KEY"), "")
    if not api_key:
        pytest.skip("No API key configured — set OPENROUTER_API_KEY in .env")
    return OpenAI(
        api_key=api_key,
        base_url=api_config.get("base_url", "https://openrouter.ai/api/v1"),
        timeout=60.0,
        max_retries=1,
    )


@pytest.fixture(scope="session")
def models_under_test(eval_config) -> list[ModelConfig]:
    return [
        ModelConfig(**cfg) for cfg in eval_config.get("models_under_test", [])
    ]


@pytest.fixture(scope="session")
def judge_models(eval_config) -> list[ModelConfig]:
    return [
        ModelConfig(**cfg) for cfg in eval_config.get("judge_models", [])
    ]


@pytest.fixture(scope="session")
def project_root() -> Path:
    return _get_project_root()


@pytest.fixture(scope="session")
def traces_dir() -> Path:
    return _get_project_root() / "traces"


def pytest_generate_tests(metafunc):
    """Parametrize tests over discovered rubrics and their scenarios."""
    if "rubric_scenario" not in metafunc.fixturenames:
        return

    project_root = _get_project_root()
    skills_dir_opt = metafunc.config.getoption("--skills-dir")
    skills_dir = Path(skills_dir_opt) if skills_dir_opt else project_root / "skills"

    rubrics = discover_rubrics(skills_dir)
    cases = []
    ids = []
    for rubric in rubrics:
        skill_name = rubric.get("skill", "unknown")
        group = rubric["_group"]
        version = rubric["_version"]
        system_prompt = load_skill_as_system_prompt(rubric["_skill_path"])
        for scenario in rubric.get("test_scenarios", []):
            cases.append({
                "rubric": rubric,
                "scenario": scenario,
                "system_prompt": system_prompt,
                "skill_name": skill_name,
                "group": group,
                "version": version,
            })
            ids.append(f"{skill_name}::{scenario['id']}")
    metafunc.parametrize("rubric_scenario", cases, ids=ids)
