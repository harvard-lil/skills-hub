"""Tests for skill packaging and inventory generation."""

from pathlib import Path
import json
import zipfile

from skills_hub_builder.discover import discover_tree
from skills_hub_builder.packager import (
    build_bundled_skills_text,
    build_inventory,
    parse_meta_sections,
    render_meta_skill_md,
    write_inventory,
    zip_skill,
    zip_meta_skill,
)

META_TEMPLATE = """{{frontmatter}}

{{intro}}

## Bundled Skills

{{bundled_skills}}

## Behavior

Defer to the bundled skills before assisting directly.

## Assist Directly

{{assist_directly}}

{{extra_sections}}

## Updates

Hub: {{hub_url}}
Inventory: {{inventory_url}}
Source: {{repo_skills_url}}
Issues: {{issues_url}}
"""


def _write_sectioned_meta(tmp_project: Path) -> None:
    """Replace the fixture's meta with one that has no inline placeholder."""
    meta = tmp_project / "skills" / "analysis" / "analysis-meta" / "SKILL.md"
    meta.write_text(
        "---\n"
        "name: analysis-meta\n"
        "description: Routes analysis tasks\n"
        "version: 0.1.0\n"
        "status: preview\n"
        "---\n\n"
        "# Analysis Pack\n\nYou route analysis work.\n\n"
        "## Assist Directly\n\n"
        "Be concise.\n\n"
        "## Boundaries\n\n"
        "Never invent data.\n",
        encoding="utf-8",
    )


def test_zip_skill(tmp_project: Path, tmp_path: Path):
    tree = discover_tree(tmp_project / "skills")
    analysis = next(c for c in tree.children if c.id == "analysis")
    skill = analysis.child_skills()[0]  # data-check

    out = tmp_path / "out" / "test.skill"
    zip_skill(skill, out)

    assert out.exists()
    with zipfile.ZipFile(out) as zf:
        names = zf.namelist()
        assert "data-check/SKILL.md" in names


def test_zip_meta_skill(tmp_project: Path, tmp_path: Path):
    tree = discover_tree(tmp_project / "skills")
    analysis = next(c for c in tree.children if c.id == "analysis")
    meta = analysis.meta_skill()
    children = analysis.child_skills()

    rendered = "# Rendered meta\n\n## Bundled\n- data-check"
    out = tmp_path / "out" / "meta.skill"
    zip_meta_skill(meta, children, out, rendered)

    assert out.exists()
    with zipfile.ZipFile(out) as zf:
        names = zf.namelist()
        assert "analysis-meta/SKILL.md" in names
        # Bundled skill is in references/
        assert "analysis-meta/references/data-check/subskill.md" in names

        # The rendered SKILL.md replaces the original
        content = zf.read("analysis-meta/SKILL.md").decode()
        assert "# Rendered meta" in content


def test_build_bundled_skills_text(tmp_project: Path):
    tree = discover_tree(tmp_project / "skills")
    analysis = next(c for c in tree.children if c.id == "analysis")
    children = analysis.child_skills()

    text = build_bundled_skills_text(children)
    assert "**data-check**" in text
    assert "v1.2.0" in text
    assert "Official" in text
    assert "references/data-check/subskill.md" in text


def test_render_meta_skill_md(tmp_project: Path):
    tree = discover_tree(tmp_project / "skills")
    analysis = next(c for c in tree.children if c.id == "analysis")
    meta = analysis.meta_skill()
    children = analysis.child_skills()

    rendered = render_meta_skill_md(
        meta, children,
        base_url="https://example.com/",
        repo_url="https://github.com/org/repo/",
        group_path="analysis",
    )

    assert "**data-check**" in rendered
    assert "{{ bundled_skills }}" not in rendered  # placeholder replaced


def test_render_meta_skill_md_substitutes_inventory_url(tmp_project: Path):
    meta_path = tmp_project / "skills" / "analysis" / "analysis-meta" / "SKILL.md"
    meta_path.write_text(
        meta_path.read_text(encoding="utf-8") + "\nInventory: {{ inventory_url }}\n",
        encoding="utf-8",
    )
    tree = discover_tree(tmp_project / "skills")
    analysis = next(c for c in tree.children if c.id == "analysis")

    rendered = render_meta_skill_md(
        analysis.meta_skill(), analysis.child_skills(),
        base_url="https://example.com/",
        repo_url="https://github.com/org/repo/",
        group_path="analysis",
    )

    assert "Inventory: https://example.com/inventory/analysis.json" in rendered


def test_parse_meta_sections():
    text = (
        "---\nname: x\n---\n\n"
        "# Title\n\nIntro prose.\n\n"
        "## Assist Directly\n\nDefaults here.\n\n"
        "## Boundaries\n\nLimits here.\n"
    )
    sections = parse_meta_sections(text)

    assert sections["frontmatter"] == "---\nname: x\n---"
    assert sections["intro"] == "# Title\n\nIntro prose."
    assert sections["assist_directly"] == "Defaults here."
    assert sections["extra_sections"] == "## Boundaries\n\nLimits here."


def test_parse_meta_sections_without_assist_directly():
    sections = parse_meta_sections("---\nname: x\n---\n\n# Title\n\nAll intro.\n")

    assert sections["intro"] == "# Title\n\nAll intro."
    assert sections["assist_directly"] == ""
    assert sections["extra_sections"] == ""


def test_render_meta_skill_md_with_wrapper_template(tmp_project: Path):
    """A consumer template composes the meta body; the skill supplies only its own prose."""
    _write_sectioned_meta(tmp_project)
    tree = discover_tree(tmp_project / "skills")
    analysis = next(c for c in tree.children if c.id == "analysis")

    rendered = render_meta_skill_md(
        analysis.meta_skill(), analysis.child_skills(),
        base_url="https://example.com/",
        repo_url="https://github.com/org/repo/",
        group_path="analysis",
        template=META_TEMPLATE,
    )

    # Frontmatter and the skill's own sections land in their template slots
    assert rendered.startswith("---\nname: analysis-meta\n")
    assert "# Analysis Pack" in rendered
    assert "Be concise." in rendered
    assert "## Boundaries\n\nNever invent data." in rendered
    # The template's shared sections are present
    assert "Defer to the bundled skills before assisting directly." in rendered
    assert "**data-check**" in rendered
    # Build-time values are substituted
    assert "Hub: https://example.com/" in rendered
    assert "Inventory: https://example.com/inventory/analysis.json" in rendered
    assert "Source: https://github.com/org/repo/tree/main/skills/analysis" in rendered
    assert "Issues: https://github.com/org/repo/issues" in rendered
    assert "{{" not in rendered


def test_build_inventory(tmp_project: Path):
    tree = discover_tree(tmp_project / "skills")
    inv = build_inventory(tree, "https://example.com/", "https://github.com/org/repo/")

    groups = inv["groups"]["groups"]
    assert len(groups) == 2

    analysis_grp = next(g for g in groups if g["id"] == "analysis")
    assert analysis_grp["label"] == "Analysis Tools"
    assert analysis_grp["skill_count"] == 1
    assert analysis_grp["meta_skill_url"] == "https://example.com/skills/analysis/analysis-meta.skill"

    monitoring_grp = next(g for g in groups if g["id"] == "monitoring")
    assert monitoring_grp["skill_count"] == 1
    assert monitoring_grp["meta_skill_url"] is None

    # Per-group inventories
    analysis_inv = inv["inventories"]["analysis"]
    assert analysis_inv["meta_skill"]["name"] == "analysis-meta"
    assert len(analysis_inv["skills"]) == 1
    assert analysis_inv["skills"][0]["name"] == "data-check"


def test_write_inventory(tmp_project: Path, tmp_path: Path):
    tree = discover_tree(tmp_project / "skills")
    inv = build_inventory(tree, "https://example.com/")
    out = tmp_path / "output"
    out.mkdir()

    write_inventory(inv, out)

    groups_json = out / "inventory" / "groups.json"
    assert groups_json.exists()
    data = json.loads(groups_json.read_text())
    assert "groups" in data
    assert len(data["groups"]) == 2

    analysis_json = out / "inventory" / "analysis.json"
    assert analysis_json.exists()
