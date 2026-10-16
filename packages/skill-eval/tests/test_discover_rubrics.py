"""Tests for finding each skill's rubric in its `_hub/` directory."""

from __future__ import annotations

from pathlib import Path

from skill_eval.conftest_plugin import discover_rubrics

SKILL_MD = "---\nname: {name}\ndescription: test\nversion: 1.2.3\n---\n\n# Test\n"


def _skill(skills_dir: Path, group: str, name: str) -> Path:
    skill_dir = skills_dir / group / name
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(SKILL_MD.format(name=name), encoding="utf-8")
    return skill_dir


def _rubric(path: Path, skill: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"skill: {skill}\ntest_scenarios: []\n", encoding="utf-8")
    return path


def test_rubric_in_hub_dir_is_paired_with_skill_md(tmp_path: Path):
    alpha = _skill(tmp_path, "grp", "alpha")
    rubric = _rubric(alpha / "_hub" / "rubric.yaml", "alpha")

    [found] = discover_rubrics(tmp_path)
    assert found["_rubric_path"] == rubric
    assert found["_skill_path"] == alpha / "SKILL.md"
    assert found["_group"] == "grp"
    assert found["_version"] == "1.2.3"


def test_skill_without_rubric_is_skipped(tmp_path: Path):
    _skill(tmp_path, "grp", "alpha")
    assert discover_rubrics(tmp_path) == []


def test_rubric_yaml_outside_hub_dir_is_not_read(tmp_path: Path):
    """`rubric.yaml` is an ordinary filename anywhere but `_hub/`."""
    alpha = _skill(tmp_path, "grp", "alpha")
    _rubric(alpha / "rubric.yaml", "alpha")
    _rubric(alpha / "references" / "rubric.yaml", "alpha")
    _rubric(tmp_path / "grp" / "no-skill" / "_hub" / "rubric.yaml", "no-skill")
    assert discover_rubrics(tmp_path) == []


def test_skill_md_under_hub_dir_is_not_a_skill(tmp_path: Path):
    alpha = _skill(tmp_path, "grp", "alpha")
    _rubric(alpha / "_hub" / "rubric.yaml", "alpha")
    nested = alpha / "_hub" / "fixture"
    nested.mkdir()
    (nested / "SKILL.md").write_text(SKILL_MD.format(name="fixture"), encoding="utf-8")
    _rubric(nested / "_hub" / "rubric.yaml", "fixture")

    assert [r["skill"] for r in discover_rubrics(tmp_path)] == ["alpha"]


def test_every_skill_with_a_rubric_is_found(tmp_path: Path):
    for name in ("alpha", "beta"):
        _rubric(_skill(tmp_path, "grp", name) / "_hub" / "rubric.yaml", name)
    assert [r["skill"] for r in discover_rubrics(tmp_path)] == ["alpha", "beta"]
