"""Main build pipeline — orchestrates discovery, packaging, and rendering."""

from __future__ import annotations

import shutil
from pathlib import Path

from .claude_extension import build_claude_extension, mcpb_download_url
from .config import HubConfig, load_config
from .discover import SkillNode, discover_tree
from .gpt_actions import build_gpt_actions
from .packager import (
    build_inventory,
    render_meta_skill_md,
    write_inventory,
    zip_meta_skill,
    zip_skill,
)
from .renderer import render_site


def build(
    project_root: Path,
    *,
    base_url: str = "",
    repo_url: str = "",
    custom_gpt_url: str = "",
) -> None:
    """Run the full build pipeline.

    Args:
        project_root: Path to the project directory (containing hub.yaml, skills/).
        base_url: Base URL for the deployed site (for absolute links).
        repo_url: GitHub/source repo URL (for edit links).
        custom_gpt_url: Published Custom GPT URL, linked from the install page.
    """
    config = load_config(project_root)
    output_dir = config.output_dir

    # Clean output
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    # Discover skill tree
    if not config.skills_dir.is_dir():
        print(f"No skills/ directory found at {config.skills_dir}")
        return

    tree = discover_tree(config.skills_dir)

    # Package skills
    if config.outputs.skill_packages:
        _package_skills(tree, config, base_url=base_url, repo_url=repo_url)

    # Generate inventory
    inv_data = build_inventory(tree, base_url, repo_url)
    write_inventory(inv_data, output_dir)

    # Render website
    if config.outputs.site:
        render_site(
            config,
            tree,
            base_url=base_url,
            repo_url=repo_url,
            custom_gpt_url=custom_gpt_url,
            mcpb_download_url=mcpb_download_url(config, base_url),
        )

    # Copy traces if they exist
    if config.traces_dir.is_dir():
        _copy_traces(config)

    # GPT Actions (static OpenAPI + JSON endpoints)
    if config.outputs.gpt_actions:
        build_gpt_actions(tree, config, base_url=base_url)

    # Claude Desktop Extension (.mcpb) — reads actions/personas.json if its
    # templates ask for it, so it runs after the actions above.
    if config.outputs.claude_extension:
        build_claude_extension(config, base_url=base_url)

    # Summary
    all_skills = tree.all_skills()
    group_count = sum(1 for c in tree.children if c.is_group)
    print(f"Built {len(all_skills)} skills across {group_count} groups")
    print(f"Output: {output_dir}")


def _package_skills(
    tree: SkillNode,
    config: HubConfig,
    *,
    base_url: str,
    repo_url: str,
) -> None:
    """Package all skills as .skill zip files."""
    output_dir = config.output_dir

    # Optional wrapper the consumer composes every meta skill into.
    meta_template_path = config.templates_dir / "meta-skill.md"
    meta_template = (
        meta_template_path.read_text(encoding="utf-8") if meta_template_path.is_file() else None
    )

    for group_node in tree.children:
        if not group_node.is_group:
            continue

        group_id = group_node.id
        child_skills = group_node.child_skills()
        meta = group_node.meta_skill()

        # Package individual skills
        for skill in child_skills:
            out_path = output_dir / "skills" / group_id / f"{skill.name}.skill"
            zip_skill(skill, out_path)

        # Package meta skill (with bundled children)
        if meta:
            rendered_md = render_meta_skill_md(
                meta,
                child_skills,
                base_url=base_url,
                repo_url=repo_url,
                group_path=group_id,
                template=meta_template,
            )
            out_path = output_dir / "skills" / group_id / f"{meta.name}.skill"
            zip_meta_skill(meta, child_skills, out_path, rendered_md)


def _copy_traces(config: HubConfig) -> None:
    """Copy trace data into the output directory.

    `index.html` is skipped: a project that ships a trace viewer keeps it in
    website/traces/, where the renderer has already written it, and copying
    the repository's own standalone viewer over it would undo that.
    """
    import shutil as _shutil

    traces_out = config.output_dir / "traces"
    traces_out.mkdir(parents=True, exist_ok=True)
    for item in config.traces_dir.rglob("*"):
        if not item.is_file():
            continue
        if item.name == "index.html":
            continue
        rel = item.relative_to(config.traces_dir)
        dest = traces_out / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        _shutil.copy2(item, dest)
