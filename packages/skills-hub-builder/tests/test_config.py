"""Tests for hub.yaml configuration loading."""

from pathlib import Path

from skills_hub_builder.config import HubConfig, load_config


def test_load_config_with_hub_yaml(tmp_project: Path):
    config = load_config(tmp_project)

    assert config.site.title == "Test Hub"
    assert config.site.subtitle == "A test skills hub"
    assert config.site.org_name == "Test Org"
    assert config.theme.exclude == ["install.html"]
    assert config.nav == [{"label": "Skills", "href": "#groups"}]
    assert config.outputs.site is True
    assert config.outputs.gpt_actions is False


def test_load_config_defaults(tmp_path: Path):
    """When no hub.yaml exists, defaults are used."""
    config = load_config(tmp_path)

    assert config.site.title == "Skills Hub"
    assert config.site.subtitle == ""
    assert config.site.org_name == ""
    assert config.theme.exclude == []
    assert config.nav == []


def test_config_paths(tmp_project: Path):
    config = load_config(tmp_project)

    assert config.skills_dir == tmp_project.resolve() / "skills"
    assert config.output_dir == tmp_project.resolve() / "_site"
    assert config.website_dir == tmp_project.resolve() / "website"
    assert config.traces_dir == tmp_project.resolve() / "traces"


def test_load_config_org_alias(tmp_path: Path):
    """'org' in site config is an alias for 'org_name'."""
    (tmp_path / "hub.yaml").write_text(
        "site:\n  org: My Org\n", encoding="utf-8"
    )
    config = load_config(tmp_path)
    assert config.site.org_name == "My Org"
