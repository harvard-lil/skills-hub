"""Integration tests for the full build pipeline."""

import json
import zipfile
from pathlib import Path

from skills_hub_builder.build import build


def test_full_build(tmp_project: Path):
    """Full build produces expected outputs."""
    build(tmp_project, base_url="https://example.com/", repo_url="https://github.com/org/repo/")

    site = tmp_project / "_site"
    assert site.exists()

    # HTML
    assert (site / "index.html").exists()

    # Static assets
    assert (site / "css" / "styles.css").exists()
    assert (site / "js" / "app.js").exists()

    # Inventory
    groups = json.loads((site / "inventory" / "groups.json").read_text())
    assert len(groups["groups"]) == 2
    assert groups["repo_url"] == "https://github.com/org/repo/"

    # Skill packages
    assert (site / "skills" / "analysis" / "data-check.skill").exists()
    assert (site / "skills" / "analysis" / "analysis-meta.skill").exists()
    assert (site / "skills" / "monitoring" / "watch-feeds.skill").exists()

    # Meta skill has bundled content
    with zipfile.ZipFile(site / "skills" / "analysis" / "analysis-meta.skill") as zf:
        md = zf.read("analysis-meta/SKILL.md").decode()
        assert "data-check" in md
        assert "{{ bundled_skills }}" not in md


def test_build_no_skills_dir(tmp_path: Path, capsys):
    """Build gracefully handles missing skills/ directory."""
    (tmp_path / "hub.yaml").write_text("site:\n  title: Empty\n", encoding="utf-8")
    build(tmp_path)

    captured = capsys.readouterr()
    assert "No skills/ directory" in captured.out


def test_build_with_traces(tmp_project: Path):
    """Traces directory is copied to output if present."""
    traces = tmp_project / "traces"
    traces.mkdir()
    (traces / "index.json").write_text('{"traces": []}', encoding="utf-8")
    sub = traces / "analysis" / "data-check" / "1.0.0"
    sub.mkdir(parents=True)
    (sub / "scenario_0001.json").write_text('{}', encoding="utf-8")

    build(tmp_project)

    site = tmp_project / "_site"
    assert (site / "traces" / "index.json").exists()
    assert (site / "traces" / "analysis" / "data-check" / "1.0.0" / "scenario_0001.json").exists()


def test_traces_index_html_does_not_overwrite_the_rendered_page(tmp_project: Path):
    """A repo's standalone traces/index.html must not clobber website/traces/index.html."""
    traces = tmp_project / "traces"
    traces.mkdir()
    (traces / "index.html").write_text("<p>STANDALONE VIEWER</p>", encoding="utf-8")
    (traces / "index.json").write_text('{"traces": []}', encoding="utf-8")

    website_traces = tmp_project / "website" / "traces"
    website_traces.mkdir(parents=True)
    (website_traces / "index.html").write_text(
        "{% extends '_base.html' %}{% block content %}<p>SITE VIEWER</p>{% endblock %}",
        encoding="utf-8",
    )

    build(tmp_project)

    rendered = (tmp_project / "_site" / "traces" / "index.html").read_text()
    assert "SITE VIEWER" in rendered
    assert "STANDALONE VIEWER" not in rendered
    # Everything else under traces/ still comes across
    assert (tmp_project / "_site" / "traces" / "index.json").exists()


def test_meta_wrapper_template_is_used_when_present(tmp_project: Path):
    """templates/meta-skill.md composes every meta skill in the project."""
    templates = tmp_project / "templates"
    templates.mkdir()
    (templates / "meta-skill.md").write_text(
        "{{frontmatter}}\n\n{{intro}}\n\n## Bundled\n\n{{bundled_skills}}\n\n"
        "## Updates\n\nInventory: {{inventory_url}}\n",
        encoding="utf-8",
    )

    build(tmp_project, base_url="https://example.com/")

    with zipfile.ZipFile(
        tmp_project / "_site" / "skills" / "analysis" / "analysis-meta.skill"
    ) as zf:
        md = zf.read("analysis-meta/SKILL.md").decode()
    assert md.startswith("---\nname: analysis-meta\n")
    assert "## Bundled" in md
    assert "**data-check**" in md
    assert "Inventory: https://example.com/inventory/analysis.json" in md


def test_meta_skill_keeps_inline_placeholders_without_a_template(tmp_project: Path):
    """Projects with no templates/ keep the placeholder-in-the-skill behavior."""
    build(tmp_project, base_url="https://example.com/")

    with zipfile.ZipFile(
        tmp_project / "_site" / "skills" / "analysis" / "analysis-meta.skill"
    ) as zf:
        md = zf.read("analysis-meta/SKILL.md").decode()
    # The fixture's own body, with its inline placeholder expanded in place
    assert "# Analysis Pack" in md
    assert "## Tools" in md
    assert "**data-check**" in md
    assert "{{ bundled_skills }}" not in md


def test_build_outputs_config(tmp_path: Path):
    """Respects outputs config — no skill packages when disabled."""
    skills = tmp_path / "skills" / "grp" / "sk"
    skills.mkdir(parents=True)
    (tmp_path / "skills" / "grp" / "group.yaml").write_text(
        "label: G\ndescription: g\n", encoding="utf-8"
    )
    (skills / "SKILL.md").write_text(
        "---\nname: sk\ndescription: d\n---\n# S\n", encoding="utf-8"
    )
    (tmp_path / "hub.yaml").write_text(
        "site:\n  title: T\noutputs:\n  skill_packages: false\n",
        encoding="utf-8",
    )

    build(tmp_path)

    site = tmp_path / "_site"
    # Inventory is always generated
    assert (site / "inventory" / "groups.json").exists()
    # But no .skill files
    assert not list(site.rglob("*.skill"))
