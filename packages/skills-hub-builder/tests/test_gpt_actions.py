"""Tests for the GPT Actions output (outputs.gpt_actions)."""

import json
from pathlib import Path

import yaml
from skills_hub_builder.build import build
from skills_hub_builder.config import load_config
from skills_hub_builder.discover import discover_tree
from skills_hub_builder.gpt_actions import (
    build_gpt_actions,
    discover_references,
    read_skill_body,
)


def _enable_actions(project: Path, extra: str = "") -> None:
    (project / "hub.yaml").write_text(
        "site:\n"
        "  title: Test Hub\n"
        "  subtitle: A test skills hub\n"
        "outputs:\n"
        "  gpt_actions: true\n" + extra,
        encoding="utf-8",
    )


def test_actions_not_written_when_flag_off(tmp_project: Path):
    """The default hub.yaml leaves gpt_actions off and writes no actions/."""
    build(tmp_project)
    assert not (tmp_project / "_site" / "actions").exists()


def test_actions_tree(tmp_project: Path):
    _enable_actions(tmp_project)
    build(tmp_project, base_url="https://example.com/")

    actions = tmp_project / "_site" / "actions"
    assert (actions / "personas.json").is_file()
    assert (actions / "openapi.json").is_file()
    assert (actions / "openapi.yaml").is_file()
    assert (actions / "personas" / "analysis.json").is_file()
    assert (actions / "personas" / "monitoring.json").is_file()
    assert (actions / "skills" / "analysis" / "data-check.json").is_file()
    # Meta skills are routers, not fetchable skills
    assert not (actions / "skills" / "analysis" / "analysis-meta.json").exists()


def test_persona_index_entry(tmp_project: Path):
    _enable_actions(tmp_project)
    build(tmp_project, base_url="https://example.com/")

    data = json.loads((tmp_project / "_site" / "actions" / "personas.json").read_text())
    entry = next(p for p in data["personas"] if p["id"] == "analysis")
    assert entry["label"] == "Analysis Tools"
    # The index description is the meta skill's — it is what a GPT matches on
    assert entry["description"] == "Routes analysis tasks"
    assert entry["objective"] == "Help with analysis"
    assert entry["skill_count"] == 1
    assert data["description"].startswith("Test Hub persona index.")


def test_persona_detail_carries_group_metadata(tmp_project: Path):
    _enable_actions(tmp_project)
    build(tmp_project, base_url="https://example.com/")

    detail = json.loads(
        (tmp_project / "_site" / "actions" / "personas" / "analysis.json").read_text()
    )
    assert detail["headline"] == "Tools for analyzing things"
    assert detail["design"]["objective"] == "Help with analysis"
    assert [s["name"] for s in detail["skills"]] == ["data-check"]
    assert detail["skills"][0]["has_references"] is False


def test_skill_detail_holds_the_body_not_the_frontmatter(tmp_project: Path):
    _enable_actions(tmp_project)
    build(tmp_project, base_url="https://example.com/")

    skill = json.loads(
        (tmp_project / "_site" / "actions" / "skills" / "analysis" / "data-check.json").read_text()
    )
    assert skill["persona"] == "analysis"
    assert skill["version"] == "1.2.0"
    assert skill["skill_body"] == "# Data Check\n\nYou check data quality."
    assert "name: data-check" not in skill["skill_body"]
    assert skill["references"] == []


def test_references_are_published_and_linked(tmp_project: Path):
    refs = tmp_project / "skills" / "analysis" / "data-check" / "references"
    refs.mkdir()
    (refs / "checklist.md").write_text("# Checklist\n", encoding="utf-8")
    (refs / "notes.txt").write_text("not markdown\n", encoding="utf-8")

    _enable_actions(tmp_project)
    build(tmp_project, base_url="https://example.com/")

    skills_out = tmp_project / "_site" / "actions" / "skills" / "analysis"
    skill = json.loads((skills_out / "data-check.json").read_text())
    assert skill["references"] == [
        {
            "name": "checklist",
            "fetch_path": "/actions/skills/analysis/data-check/references/checklist",
        }
    ]
    assert "fetch them as needed" in skill["usage_hint"]

    ref = json.loads((skills_out / "data-check" / "references" / "checklist.json").read_text())
    assert ref["content"] == "# Checklist\n"
    assert ref["skill"] == "data-check"
    # Non-markdown files in references/ are not published
    assert not (skills_out / "data-check" / "references" / "notes.json").exists()


def test_openapi_spec(tmp_project: Path):
    _enable_actions(tmp_project)
    build(tmp_project, base_url="https://example.com/hub/")

    spec = json.loads((tmp_project / "_site" / "actions" / "openapi.json").read_text())
    assert spec["info"]["title"] == "Test Hub"
    assert spec["info"]["description"] == "A test skills hub"
    # The trailing slash is stripped: paths in the spec supply their own
    assert spec["servers"] == [{"url": "https://example.com/hub"}]

    params = spec["paths"]["/actions/personas/{persona_id}.json"]["get"]["parameters"]
    assert params[0]["schema"]["enum"] == ["analysis", "monitoring"]

    yaml_spec = yaml.safe_load((tmp_project / "_site" / "actions" / "openapi.yaml").read_text())
    assert yaml_spec == spec


def test_actions_title_overrides_site_title(tmp_project: Path):
    _enable_actions(
        tmp_project,
        "actions:\n  title: Custom GPT Name\n  description: Its own blurb\n",
    )
    build(tmp_project, base_url="https://example.com/")

    spec = json.loads((tmp_project / "_site" / "actions" / "openapi.json").read_text())
    assert spec["info"]["title"] == "Custom GPT Name"
    assert spec["info"]["description"] == "Its own blurb"

    index = json.loads((tmp_project / "_site" / "actions" / "personas.json").read_text())
    assert index["description"].startswith("Custom GPT Name persona index.")


def test_read_skill_body_and_references_helpers(tmp_project: Path):
    skill_dir = tmp_project / "skills" / "analysis" / "data-check"
    assert read_skill_body(skill_dir / "SKILL.md").startswith("# Data Check")
    assert discover_references(skill_dir) == []


def test_build_gpt_actions_is_callable_alone(tmp_project: Path):
    """The generator does not depend on the rest of the pipeline having run."""
    _enable_actions(tmp_project)
    config = load_config(tmp_project)
    tree = discover_tree(config.skills_dir)
    config.output_dir.mkdir(parents=True, exist_ok=True)

    build_gpt_actions(tree, config, base_url="")

    spec = json.loads((config.output_dir / "actions" / "openapi.json").read_text())
    assert spec["servers"] == [{"url": "https://example.github.io/skills-hub-demo"}]
