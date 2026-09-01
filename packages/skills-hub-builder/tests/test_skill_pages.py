"""Tests for per-skill pages and the draft/official status vocabulary."""

from __future__ import annotations

import json
from pathlib import Path

from skills_hub_builder.build import build
from skills_hub_builder.config import load_config
from skills_hub_builder.discover import discover_tree, normalize_status
from skills_hub_builder.skill_pages import (
    package_files,
    render_body_html,
    strip_frontmatter,
    strip_leading_h1,
)


class TestStatusVocabulary:
    def test_preview_is_read_as_draft(self):
        assert normalize_status("preview") == "draft"

    def test_missing_status_is_draft(self):
        assert normalize_status("") == "draft"

    def test_official_survives(self):
        assert normalize_status("Official") == "official"

    def test_unknown_status_passes_through(self):
        assert normalize_status("retired") == "retired"

    def test_discovered_skill_carries_normalized_status(self, tmp_project: Path):
        tree = discover_tree(tmp_project / "skills")
        statuses = {s.name: s.status for s in tree.all_skills()}
        assert statuses["data-check"] == "official"
        assert statuses["watch-feeds"] == "draft"  # written as `preview`


class TestMarkdownHelpers:
    def test_strip_frontmatter(self):
        text = "---\nname: x\n---\n\n# Title\n\nBody.\n"
        assert strip_frontmatter(text).strip() == "# Title\n\nBody."

    def test_strip_leading_h1_only_at_the_top(self):
        assert strip_leading_h1("# Title\n\nBody\n\n# Later\n") == "Body\n\n# Later\n"

    def test_body_html_escapes_raw_html(self):
        html = render_body_html("---\nname: x\n---\n\nUse <placeholder> here.\n")
        assert "&lt;placeholder&gt;" in html

    def test_package_files_lists_nested_files(self, tmp_project: Path):
        tree = discover_tree(tmp_project / "skills")
        skill = next(s for s in tree.all_skills() if s.name == "data-check")
        (skill.dir / "references").mkdir()
        (skill.dir / "references" / "notes.md").write_text("notes", encoding="utf-8")
        assert package_files(skill) == ["SKILL.md", "references/notes.md"]


class TestSkillPages:
    def test_a_page_is_written_for_every_skill(self, tmp_project: Path):
        build(tmp_project)
        site = tmp_project / "_site"
        assert (site / "skills" / "analysis" / "data-check.html").is_file()
        assert (site / "skills" / "analysis" / "analysis-meta.html").is_file()
        assert (site / "skills" / "monitoring" / "watch-feeds.html").is_file()

    def test_draft_page_says_so_and_official_does_not(self, tmp_project: Path):
        build(tmp_project)
        site = tmp_project / "_site"
        draft = (site / "skills" / "monitoring" / "watch-feeds.html").read_text(encoding="utf-8")
        official = (site / "skills" / "analysis" / "data-check.html").read_text(encoding="utf-8")

        assert "This is a draft." in draft
        assert 'skill-status-draft' in draft
        assert "This is a draft." not in official
        assert 'skill-status-official' in official

    def test_page_renders_the_skill_body(self, tmp_project: Path):
        build(tmp_project)
        page = (tmp_project / "_site" / "skills" / "monitoring" / "watch-feeds.html").read_text(
            encoding="utf-8"
        )
        assert "<p>You monitor feeds.</p>" in page
        # Frontmatter is not published, and the body's own title is not repeated.
        assert "name: watch-feeds" not in page
        # The header prints the title; the body's own `# Watch Feeds` is dropped.
        assert page.count("<h1>Watch Feeds</h1>") == 1

    def test_meta_page_shows_the_composed_body(self, tmp_project: Path):
        build(tmp_project)
        page = (tmp_project / "_site" / "skills" / "analysis" / "analysis-meta.html").read_text(
            encoding="utf-8"
        )
        assert "{{ bundled_skills }}" not in page
        assert "data-check" in page

    def test_page_nav_resolves_from_a_subdirectory(self, tmp_project: Path):
        build(tmp_project)
        page = (tmp_project / "_site" / "skills" / "monitoring" / "watch-feeds.html").read_text(
            encoding="utf-8"
        )
        assert 'href="../../index.html#groups"' in page

    def test_inventory_links_to_the_page(self, tmp_project: Path):
        build(tmp_project)
        inv = json.loads(
            (tmp_project / "_site" / "inventory" / "monitoring.json").read_text(encoding="utf-8")
        )
        assert inv["skills"][0]["page_url"] == "skills/monitoring/watch-feeds.html"

    def test_pages_are_skipped_when_the_site_is_off(self, tmp_project: Path):
        config_path = tmp_project / "hub.yaml"
        config_path.write_text(
            config_path.read_text(encoding="utf-8") + "outputs:\n  site: false\n",
            encoding="utf-8",
        )
        assert load_config(tmp_project).outputs.site is False
        build(tmp_project)
        assert not (tmp_project / "_site" / "skills" / "monitoring" / "watch-feeds.html").exists()
