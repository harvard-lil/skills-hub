"""CLI entry point for skills-hub-builder."""

from __future__ import annotations

from pathlib import Path

import click


@click.group()
def main():
    """Skills Hub Builder — generate a static site from a collection of agent skills."""
    pass


@main.command()
@click.option(
    "--project", "-p",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=".",
    help="Project root directory (containing hub.yaml and skills/). Defaults to current directory.",
)
@click.option(
    "--base-url",
    default="",
    envvar="BASE_URL",
    help="Base URL for the deployed site (e.g., https://org.github.io/repo/).",
)
@click.option(
    "--repo-url",
    default="",
    envvar="REPO_URL",
    help="Source repository URL (for edit/contribute links).",
)
@click.option(
    "--custom-gpt-url",
    default="",
    envvar="CUSTOM_GPT_URL",
    help="Published Custom GPT URL, linked from the install page. Empty hides the link.",
)
def build(project: Path, base_url: str, repo_url: str, custom_gpt_url: str):
    """Build the skills hub site from the project directory."""
    from .build import build as run_build

    run_build(project, base_url=base_url, repo_url=repo_url, custom_gpt_url=custom_gpt_url)


@main.command()
@click.option(
    "--project", "-p",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=".",
    help="Project root directory.",
)
def inspect(project: Path):
    """Show the discovered skill tree without building."""
    from .config import load_config
    from .discover import discover_tree

    config = load_config(project)
    if not config.skills_dir.is_dir():
        click.echo(f"No skills/ directory found at {config.skills_dir}")
        return

    tree = discover_tree(config.skills_dir)
    _print_tree(tree, indent=0)


def _print_tree(node, indent: int = 0):
    """Pretty-print the skill tree."""
    prefix = "  " * indent
    markers = []
    if node.is_group:
        markers.append("group")
    if node.is_skill:
        markers.append(f"skill:{node.skill.name}")
    marker_str = f" [{', '.join(markers)}]" if markers else ""

    click.echo(f"{prefix}{node.id}{marker_str}")

    if node.skill and not node.skill.is_meta:
        click.echo(f"{prefix}  → {node.skill.description[:80]}")

    for child in node.children:
        _print_tree(child, indent + 1)
