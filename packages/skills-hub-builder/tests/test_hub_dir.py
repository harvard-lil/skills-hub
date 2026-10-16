"""Tests for the `_hub/` directory and the README.md guide.

A skill's `_hub/` holds files the hub uses and never ships; its `README.md`
is a guide for the person using the skill, and ships like any other file.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest
from skills_hub_builder.build import build
from skills_hub_builder.discover import discover_tree, load_hub_metadata
from skills_hub_builder.packager import build_inventory, zip_meta_skill, zip_skill
from skills_hub_builder.skill_pages import package_files


def _skill_dir(project: Path) -> Path:
    return project / "skills" / "analysis" / "data-check"


@pytest.fixture
def hub_project(tmp_project: Path) -> Path:
    """tmp_project with data-check given a `_hub/`, a rubric, and a guide."""
    skill = _skill_dir(tmp_project)
    (skill / "_hub").mkdir()
    (skill / "_hub" / "metadata.yaml").write_text(
        "summary: >\n  Find the problems in a spreadsheet before you rely on it.\n",
        encoding="utf-8",
    )
    (skill / "_hub" / "rubric.yaml").write_text("skill: data-check\n", encoding="utf-8")
    (skill / "README.md").write_text(
        "# Data Check\n\nAttach a spreadsheet and ask what is wrong with it.\n",
        encoding="utf-8",
    )
    return tmp_project


def _data_check(project: Path):
    tree = discover_tree(project / "skills")
    return next(s for s in tree.all_skills() if s.name == "data-check")


class TestHubMetadata:
    def test_summary_is_read_from_hub_metadata(self, hub_project: Path):
        skill = _data_check(hub_project)
        assert skill.summary == "Find the problems in a spreadsheet before you rely on it."
        # The agent-facing description is untouched.
        assert skill.description == "Checks data quality"

    def test_summary_is_empty_without_hub_metadata(self, tmp_project: Path):
        assert _data_check(tmp_project).summary == ""

    def test_empty_metadata_file_is_allowed(self, tmp_path: Path):
        (tmp_path / "_hub").mkdir()
        (tmp_path / "_hub" / "metadata.yaml").write_text("", encoding="utf-8")
        assert load_hub_metadata(tmp_path) == {}

    def test_non_mapping_metadata_raises(self, tmp_path: Path):
        (tmp_path / "_hub").mkdir()
        (tmp_path / "_hub" / "metadata.yaml").write_text("- a\n- b\n", encoding="utf-8")
        with pytest.raises(TypeError, match="mapping"):
            load_hub_metadata(tmp_path)

    def test_non_string_summary_raises(self, tmp_path: Path):
        (tmp_path / "_hub").mkdir()
        (tmp_path / "_hub" / "metadata.yaml").write_text("summary: [a]\n", encoding="utf-8")
        with pytest.raises(TypeError, match="summary"):
            load_hub_metadata(tmp_path)

    def test_hub_dir_is_not_discovered_as_a_skill_or_group(self, hub_project: Path):
        tree = discover_tree(hub_project / "skills")
        analysis = next(c for c in tree.children if c.id == "analysis")
        data_check = next(c for c in analysis.children if c.id == "data-check")
        assert data_check.children == []

    def test_guide_path(self, hub_project: Path, tmp_project: Path):
        assert _data_check(hub_project).guide_path == _skill_dir(hub_project) / "README.md"


class TestPackaging:
    def test_skill_zip_ships_guide_but_not_hub_dir(self, hub_project: Path, tmp_path: Path):
        out = tmp_path / "data-check.skill"
        zip_skill(_data_check(hub_project), out)
        with zipfile.ZipFile(out) as zf:
            names = set(zf.namelist())
        assert names == {"data-check/SKILL.md", "data-check/README.md"}

    def test_meta_zip_leaves_out_bundled_skills_hub_dirs(self, hub_project: Path, tmp_path: Path):
        tree = discover_tree(hub_project / "skills")
        analysis = next(c for c in tree.children if c.id == "analysis")
        meta = analysis.meta_skill()
        (meta.dir / "_hub").mkdir()
        (meta.dir / "_hub" / "metadata.yaml").write_text("summary: Pack\n", encoding="utf-8")

        out = tmp_path / "meta.skill"
        zip_meta_skill(meta, analysis.child_skills(), out, "# Rendered")
        with zipfile.ZipFile(out) as zf:
            names = zf.namelist()
        assert not [n for n in names if "_hub" in n]
        assert "analysis-meta/references/data-check/README.md" in names

    def test_page_file_list_matches_package(self, hub_project: Path):
        assert package_files(_data_check(hub_project)) == ["README.md", "SKILL.md"]

    def test_hub_dir_below_the_skill_root_is_packaged(self, hub_project: Path, tmp_path: Path):
        """Only the skill's own `_hub/` is hub-only; a nested one is content."""
        nested = _skill_dir(hub_project) / "references" / "_hub"
        nested.mkdir(parents=True)
        (nested / "notes.md").write_text("notes", encoding="utf-8")
        assert "references/_hub/notes.md" in package_files(_data_check(hub_project))


class TestInventoryAndSite:
    def test_inventory_carries_summary_and_guide_flag(self, hub_project: Path):
        tree = discover_tree(hub_project / "skills")
        inv = build_inventory(tree, "https://example.com/")["inventories"]
        data_check = inv["analysis"]["skills"][0]
        assert data_check["summary"].startswith("Find the problems")
        assert data_check["description"] == "Checks data quality"
        assert data_check["has_guide"] is True

        watch = inv["monitoring"]["skills"][0]
        assert watch["summary"] is None
        assert watch["has_guide"] is False

    def test_build_ships_no_hub_files(self, hub_project: Path):
        build(hub_project)
        with zipfile.ZipFile(hub_project / "_site/skills/analysis/data-check.skill") as zf:
            assert "data-check/_hub/rubric.yaml" not in zf.namelist()
        inv = json.loads((hub_project / "_site/inventory/analysis.json").read_text())
        assert inv["skills"][0]["has_guide"] is True

    def test_page_leads_with_guide_then_instructions(self, hub_project: Path):
        build(hub_project)
        page = (hub_project / "_site/skills/analysis/data-check.html").read_text(encoding="utf-8")
        guide = page.index("Attach a spreadsheet and ask what is wrong with it.")
        instructions = page.index("You check data quality.")
        assert page.index("Using this skill") < guide < page.index("Instructions the agent reads") < instructions
        # The header shows the summary, and the guide's own title is not repeated.
        assert "Find the problems in a spreadsheet" in page
        assert page.count("<h1>Data Check</h1>") == 1

    def test_page_without_guide_is_unchanged(self, tmp_project: Path):
        build(tmp_project)
        page = (tmp_project / "_site/skills/analysis/data-check.html").read_text(encoding="utf-8")
        assert "Using this skill" not in page
        assert "Instructions the agent reads" not in page
        assert "<p>You check data quality.</p>" in page

