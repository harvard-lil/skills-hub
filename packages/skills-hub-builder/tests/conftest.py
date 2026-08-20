"""Shared fixtures for skills-hub-builder tests."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """Create a minimal project structure in a temp directory."""
    skills = tmp_path / "skills"
    skills.mkdir()

    # Group with group.yaml
    grp = skills / "analysis"
    grp.mkdir()
    (grp / "group.yaml").write_text(
        "label: Analysis Tools\n"
        "description: Tools for analyzing things\n"
        "design:\n"
        "  objective: Help with analysis\n"
        "accent_color: '#8b5cf6'\n",
        encoding="utf-8",
    )

    # A regular skill
    sk = grp / "data-check"
    sk.mkdir()
    (sk / "SKILL.md").write_text(
        "---\n"
        "name: data-check\n"
        "description: Checks data quality\n"
        "version: 1.2.0\n"
        "status: official\n"
        "---\n\n"
        "# Data Check\n\nYou check data quality.\n",
        encoding="utf-8",
    )

    # A meta skill
    meta = grp / "analysis-meta"
    meta.mkdir()
    (meta / "SKILL.md").write_text(
        "---\n"
        "name: analysis-meta\n"
        "description: Routes analysis tasks\n"
        "version: 0.1.0\n"
        "status: preview\n"
        "---\n\n"
        "# Analysis Pack\n\n## Tools\n\n{{ bundled_skills }}\n",
        encoding="utf-8",
    )

    # A second group (no group.yaml, just skills)
    grp2 = skills / "monitoring"
    grp2.mkdir()
    sk2 = grp2 / "watch-feeds"
    sk2.mkdir()
    (sk2 / "SKILL.md").write_text(
        "---\n"
        "name: watch-feeds\n"
        "description: Monitors RSS feeds for changes\n"
        "version: 0.2.0\n"
        "status: preview\n"
        "---\n\n"
        "# Watch Feeds\n\nYou monitor feeds.\n",
        encoding="utf-8",
    )

    # hub.yaml
    (tmp_path / "hub.yaml").write_text(
        "site:\n"
        "  title: Test Hub\n"
        "  subtitle: A test skills hub\n"
        "  org_name: Test Org\n"
        "theme:\n"
        "  exclude:\n"
        "    - install.html\n"
        "nav:\n"
        "  - label: Skills\n"
        "    href: '#groups'\n",
        encoding="utf-8",
    )

    return tmp_path
