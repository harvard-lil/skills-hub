"""Render Jinja2 templates to produce the static site."""

from __future__ import annotations

import shutil
from pathlib import Path

import jinja2

from .config import HubConfig
from .discover import SkillNode

# Default theme ships with the package
THEME_DIR = Path(__file__).parent / "theme"


def build_template_env(config: HubConfig) -> jinja2.Environment:
    """Create a Jinja2 environment with layered template loading.

    Templates are resolved in order:
      1. Project's website/ directory (overrides)
      2. Default theme (fallbacks)
    """
    loaders = []

    # Project-level overrides
    if config.website_dir.is_dir():
        loaders.append(jinja2.FileSystemLoader(str(config.website_dir)))

    # Default theme (always available as fallback)
    loaders.append(jinja2.FileSystemLoader(str(THEME_DIR)))

    loader = jinja2.ChoiceLoader(loaders)

    return jinja2.Environment(
        loader=loader,
        autoescape=False,
        keep_trailing_newline=True,
    )


def render_site(
    config: HubConfig,
    tree: SkillNode,
    *,
    base_url: str = "",
    repo_url: str = "",
    custom_gpt_url: str = "",
    mcpb_download_url: str = "",
) -> None:
    """Render all HTML templates and copy static assets to _site/.

    Templates starting with _ are partials (not rendered directly).
    Templates listed in config.theme.exclude are skipped.
    """
    output_dir = config.output_dir
    env = build_template_env(config)
    excluded = set(config.theme.exclude)

    # Discover all .html templates from both sources
    template_paths = _discover_templates(config)

    for rel_path in sorted(template_paths):
        # Skip partials
        if rel_path.name.startswith("_"):
            continue
        # Skip excluded
        if str(rel_path) in excluded:
            continue

        # Compute relative root for asset references
        depth = len(rel_path.parts) - 1
        root = "../" * depth

        # Gather context available to all templates
        context = {
            "config": config,
            "site": config.site,
            "tree": tree,
            "groups": tree.children,
            "base_url": base_url,
            "repo_url": repo_url,
            "root": root,
            "custom_gpt_url": custom_gpt_url,
            "mcpb_download_url": mcpb_download_url,
        }
        context["nav"] = expand_nav(config.nav, env, context)

        template = env.get_template(str(rel_path))
        rendered = template.render(**context)

        dest = output_dir / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(rendered, encoding="utf-8")

    # Copy static assets (non-HTML files) from theme and project website/
    _copy_static_assets(THEME_DIR, output_dir, excluded)
    if config.website_dir.is_dir():
        _copy_static_assets(config.website_dir, output_dir, excluded)


def expand_nav(
    nav: list[dict[str, str]],
    env: jinja2.Environment,
    context: dict,
) -> list[dict[str, str]]:
    """Render the template variables inside nav entries.

    Jinja renders a template's own text, not the strings a template is handed,
    so a `href: "{{ repo_url }}"` in hub.yaml reaches the page verbatim unless
    it is rendered here first. Each string value gets the same context as the
    page, so `{{ repo_url }}`, `{{ base_url }}` and `{{ root }}` all work.

    An entry whose href renders empty is dropped rather than published as a
    dead `href=""` — a build with no --repo-url simply has no GitHub link.
    """
    expanded = []
    for item in nav:
        rendered = {
            key: env.from_string(value).render(**context) if isinstance(value, str) else value
            for key, value in item.items()
        }
        href = rendered.get("href")
        if href is not None and not href.strip():
            continue
        expanded.append(rendered)
    return expanded


def _discover_templates(config: HubConfig) -> set[Path]:
    """Find all .html template paths (relative) from both theme and project."""
    paths = set()

    # Default theme templates
    for html_path in THEME_DIR.rglob("*.html"):
        paths.add(html_path.relative_to(THEME_DIR))

    # Project overrides (may shadow theme templates, or add new ones)
    if config.website_dir.is_dir():
        for html_path in config.website_dir.rglob("*.html"):
            paths.add(html_path.relative_to(config.website_dir))

    return paths


def _copy_static_assets(source_dir: Path, output_dir: Path, excluded: set[str]) -> None:
    """Copy non-HTML files from source to output."""
    for item in source_dir.rglob("*"):
        if not item.is_file():
            continue
        if item.suffix == ".html":
            continue
        if item.name.startswith("_") or item.name.startswith("."):
            continue

        rel = item.relative_to(source_dir)
        if str(rel) in excluded:
            continue

        dest = output_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, dest)
