"""Tests for Jinja2 template rendering."""

from pathlib import Path

from skills_hub_builder.config import load_config
from skills_hub_builder.discover import discover_tree
from skills_hub_builder.renderer import render_site, _discover_templates, build_template_env


def test_render_site_produces_index(tmp_project: Path):
    config = load_config(tmp_project)
    tree = discover_tree(config.skills_dir)
    config.output_dir.mkdir(parents=True, exist_ok=True)

    render_site(config, tree, base_url="https://example.com/")

    index = config.output_dir / "index.html"
    assert index.exists()
    content = index.read_text()
    assert "Test Hub" in content
    assert "TEST ORG" in content


def test_render_site_copies_static_assets(tmp_project: Path):
    config = load_config(tmp_project)
    tree = discover_tree(config.skills_dir)
    config.output_dir.mkdir(parents=True, exist_ok=True)

    render_site(config, tree)

    css = config.output_dir / "css" / "styles.css"
    assert css.exists()

    js = config.output_dir / "js" / "app.js"
    assert js.exists()


def test_theme_exclude(tmp_project: Path):
    """Templates listed in theme.exclude are not rendered."""
    # Add install.html to the theme so we can verify exclusion
    # (the default theme doesn't have install.html, but let's create one in website/)
    website = tmp_project / "website"
    website.mkdir()
    (website / "install.html").write_text(
        "{% extends '_base.html' %}{% block content %}<p>install</p>{% endblock %}",
        encoding="utf-8",
    )

    config = load_config(tmp_project)
    tree = discover_tree(config.skills_dir)
    config.output_dir.mkdir(parents=True, exist_ok=True)

    render_site(config, tree)

    # install.html is in the exclude list in hub.yaml
    assert not (config.output_dir / "install.html").exists()
    # index.html should still be rendered
    assert (config.output_dir / "index.html").exists()


def test_project_template_overrides_theme(tmp_project: Path):
    """A template in website/ overrides the default theme's version."""
    website = tmp_project / "website"
    website.mkdir()
    (website / "index.html").write_text(
        "{% extends '_base.html' %}{% block content %}<p>CUSTOM CONTENT</p>{% endblock %}",
        encoding="utf-8",
    )

    config = load_config(tmp_project)
    tree = discover_tree(config.skills_dir)
    config.output_dir.mkdir(parents=True, exist_ok=True)

    render_site(config, tree)

    content = (config.output_dir / "index.html").read_text()
    assert "CUSTOM CONTENT" in content
    # Still uses base template (header from theme)
    assert "TEST ORG" in content


def test_project_adds_new_page(tmp_project: Path):
    """A new .html file in website/ is rendered as an additional page."""
    website = tmp_project / "website"
    website.mkdir()
    (website / "about.html").write_text(
        "{% extends '_base.html' %}{% block content %}<p>About us</p>{% endblock %}",
        encoding="utf-8",
    )

    config = load_config(tmp_project)
    tree = discover_tree(config.skills_dir)
    config.output_dir.mkdir(parents=True, exist_ok=True)

    render_site(config, tree)

    about = config.output_dir / "about.html"
    assert about.exists()
    assert "About us" in about.read_text()


def _nav_project(tmp_project: Path, nav_yaml: str) -> Path:
    (tmp_project / "hub.yaml").write_text(
        "site:\n  title: Test Hub\nnav:\n" + nav_yaml, encoding="utf-8"
    )
    website = tmp_project / "website"
    website.mkdir(exist_ok=True)
    (website / "index.html").write_text(
        "{% for item in nav %}<a href=\"{{ item.href }}\">{{ item.label }}</a>{% endfor %}",
        encoding="utf-8",
    )
    return tmp_project


def _render(tmp_project: Path, **kwargs) -> str:
    config = load_config(tmp_project)
    tree = discover_tree(config.skills_dir)
    config.output_dir.mkdir(parents=True, exist_ok=True)
    render_site(config, tree, **kwargs)
    return (config.output_dir / "index.html").read_text()


def test_nav_href_is_template_expanded(tmp_project: Path):
    """hub.yaml nav values are rendered, not passed through verbatim."""
    _nav_project(tmp_project, "  - label: GitHub\n    href: '{{ repo_url }}'\n")

    html = _render(tmp_project, repo_url="https://github.com/org/repo/")

    assert '<a href="https://github.com/org/repo/">GitHub</a>' in html
    assert "{{ repo_url }}" not in html


def test_nav_label_is_template_expanded(tmp_project: Path):
    _nav_project(tmp_project, "  - label: '{{ site.title }} docs'\n    href: 'docs/'\n")

    html = _render(tmp_project)

    assert ">Test Hub docs</a>" in html


def test_nav_entry_with_empty_href_is_dropped(tmp_project: Path):
    """A local build with no --repo-url loses the link rather than publishing href=''."""
    _nav_project(
        tmp_project,
        "  - label: Skills\n    href: '#groups'\n"
        "  - label: GitHub\n    href: '{{ repo_url }}'\n",
    )

    html = _render(tmp_project)

    assert '<a href="#groups">Skills</a>' in html
    assert "GitHub" not in html
    assert 'href=""' not in html


def test_nav_relative_href_is_left_alone(tmp_project: Path):
    _nav_project(tmp_project, "  - label: Traces\n    href: 'traces/'\n")

    html = _render(tmp_project, repo_url="https://github.com/org/repo/")

    assert '<a href="traces/">Traces</a>' in html


def test_discover_templates_finds_theme_and_project(tmp_project: Path):
    website = tmp_project / "website"
    website.mkdir()
    (website / "custom.html").write_text("<p>custom</p>", encoding="utf-8")

    config = load_config(tmp_project)
    templates = _discover_templates(config)

    # Should find index.html from theme and custom.html from project
    rel_names = {str(t) for t in templates}
    assert "index.html" in rel_names
    assert "custom.html" in rel_names
    # Partials are discovered but skipped during rendering
    assert "_base.html" in rel_names


class TestInstallPage:
    def test_theme_install_page_renders_by_default(self, tmp_project: Path):
        from skills_hub_builder.build import build

        # The shared fixture excludes install.html; this test wants the default.
        (tmp_project / "hub.yaml").write_text(
            "site:\n  title: Test Hub\n  subtitle: A test skills hub\n",
            encoding="utf-8",
        )
        build(tmp_project)
        install = tmp_project / "_site" / "install.html"
        assert install.exists()
        text = install.read_text(encoding="utf-8")
        assert "Get Started" in text
        assert "Agent Skills" in text
        # No one-click tier without custom_gpt_url / mcpb_download_url
        assert "Custom GPT" not in text
        assert ".mcpb" not in text
        # No GitHub card without repo_url
        assert "View on GitHub" not in text

    def test_consumer_override_shadows_theme_install(self, tmp_project: Path):
        from skills_hub_builder.build import build

        (tmp_project / "hub.yaml").write_text(
            "site:\n  title: Test Hub\n  subtitle: A test skills hub\n",
            encoding="utf-8",
        )
        website = tmp_project / "website"
        website.mkdir()
        (website / "install.html").write_text("<html>custom install</html>", encoding="utf-8")

        build(tmp_project)
        text = (tmp_project / "_site" / "install.html").read_text(encoding="utf-8")
        assert text == "<html>custom install</html>"
