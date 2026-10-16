"""Tests for pairing rubric.yaml files with the SKILL.md they evaluate."""

from __future__ import annotations

from pathlib import Path

import pytest
from skill_eval.conftest_plugin import (
    RubricWithoutSkillError,
    discover_rubrics,
    skill_md_for_rubric,
)

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


def test_rubric_in_hub_dir_pairs_with_skill_md(tmp_path: Path):
    skill_dir = _skill(tmp_path, "grp", "alpha")
    rubric = _rubric(skill_dir / "_hub" / "rubric.yaml", "alpha")
    assert skill_md_for_rubric(rubric) == skill_dir / "SKILL.md"


def test_rubric_beside_skill_md_still_pairs(tmp_path: Path):
    skill_dir = _skill(tmp_path, "grp", "alpha")
    rubric = _rubric(skill_dir / "rubric.yaml", "alpha")
    assert skill_md_for_rubric(rubric) == skill_dir / "SKILL.md"


def test_orphan_rubric_raises(tmp_path: Path):
    rubric = _rubric(tmp_path / "grp" / "alpha" / "rubric.yaml", "alpha")
    with pytest.raises(RubricWithoutSkillError, match="_hub/rubric.yaml"):
        skill_md_for_rubric(rubric)


def test_rubric_nested_below_hub_dir_raises(tmp_path: Path):
    skill_dir = _skill(tmp_path, "grp", "alpha")
    rubric = _rubric(skill_dir / "_hub" / "evals" / "rubric.yaml", "alpha")
    with pytest.raises(RubricWithoutSkillError):
        skill_md_for_rubric(rubric)


def test_discover_rubrics_reads_both_layouts(tmp_path: Path):
    alpha = _skill(tmp_path, "grp", "alpha")
    beta = _skill(tmp_path, "grp", "beta")
    _rubric(alpha / "_hub" / "rubric.yaml", "alpha")
    _rubric(beta / "rubric.yaml", "beta")

    rubrics = {r["skill"]: r for r in discover_rubrics(tmp_path)}
    assert set(rubrics) == {"alpha", "beta"}
    assert rubrics["alpha"]["_skill_path"] == alpha / "SKILL.md"
    assert rubrics["alpha"]["_group"] == "grp"
    assert rubrics["alpha"]["_version"] == "1.2.3"


def test_discover_rubrics_stops_on_orphan(tmp_path: Path):
    alpha = _skill(tmp_path, "grp", "alpha")
    _rubric(alpha / "_hub" / "rubric.yaml", "alpha")
    _rubric(tmp_path / "grp" / "stray" / "rubric.yaml", "stray")
    with pytest.raises(RubricWithoutSkillError):
        discover_rubrics(tmp_path)
