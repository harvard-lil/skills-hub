"""Render one HTML page per skill, showing the SKILL.md a visitor would install.

A hub's index lists skills; these pages let someone read one before deciding to
download it, which is what the site otherwise asks them to take on faith. A meta
skill's page shows the composed body that its `.skill` package carries, not the
template with `{{ bundled_skills }}` still in it.

Pages are written to `skills/<group>/<name>.html`, alongside the `.skill` zips,
and are linked from the cards by `page_url` in the inventory JSON.
"""

from __future__ import annotations

import re
from pathlib import Path

import jinja2
from markdown_it import MarkdownIt

from .config import HubConfig
from .discover import SkillInfo, SkillNode
from .packager import load_meta_template, render_meta_skill_md
from .renderer import expand_nav

#: Files that are part of the package but not worth listing as content.
_HIDDEN_FILES = {".DS_Store"}


def _markdown() -> MarkdownIt:
    """A CommonMark renderer with tables and with raw HTML disabled.

    Skill bodies are prose written for agents, and some of them contain angle
    brackets in placeholder syntax; escaping raw HTML keeps those visible
    instead of silently swallowing them into the page.
    """
    return MarkdownIt("commonmark", {"html": False, "linkify": False}).enable("table")


def strip_frontmatter(text: str) -> str:
    """Return a SKILL.md body without its YAML frontmatter block."""
    m = re.match(r"^---\s*\n.*?\n---\s*\n?", text, re.DOTALL)
    return text[m.end():] if m else text


def strip_leading_h1(body: str) -> str:
    """Drop a body's opening `# Heading`.

    The page already prints the skill's name as its heading, so a body that
    opens with its own title would render it twice.
    """
    return re.sub(r"\A\s*#\s+[^\n]*\n+", "", body)


def render_body_html(markdown_text: str) -> str:
    """Render skill markdown to the HTML fragment the page embeds."""
    body = strip_leading_h1(strip_frontmatter(markdown_text))
    return _markdown().render(body)


def package_files(skill: SkillInfo) -> list[str]:
    """List the files a skill's `.skill` package carries, relative to its root."""
    files = []
    for path in sorted(skill.dir.rglob("*")):
        if not path.is_file() or path.name in _HIDDEN_FILES:
            continue
        files.append(str(path.relative_to(skill.dir)))
    return files


def format_title(name: str) -> str:
    """Turn a skill's hyphenated name into a display title."""
    return name.replace("-", " ").title()


def _page_nav(
    nav: list[dict[str, str]],
    env: jinja2.Environment,
    context: dict,
    root: str,
) -> list[dict[str, str]]:
    """Rewrite the site nav so it works from a page two directories down.

    hub.yaml writes hrefs as the index page sees them — `#groups`,
    `install.html` — so a page under `skills/<group>/` has to resolve them
    against the site root rather than against itself.
    """
    rewritten = []
    for item in expand_nav(nav, env, context):
        href = item.get("href", "")
        if href.startswith("#"):
            item = {**item, "href": f"{root}index.html{href}"}
        elif not href.startswith(("http://", "https://", "//", "/", "mailto:")):
            item = {**item, "href": f"{root}{href}"}
        rewritten.append(item)
    return rewritten


def build_skill_pages(
    tree: SkillNode,
    config: HubConfig,
    env: jinja2.Environment,
    *,
    base_url: str = "",
    repo_url: str = "",
) -> list[Path]:
    """Write a page for every skill and meta skill. Returns the paths written."""
    template = env.get_template("_skill.html")
    meta_template = load_meta_template(config)
    root = "../../"
    nav = _page_nav(
        config.nav,
        env,
        {"config": config, "site": config.site, "base_url": base_url,
         "repo_url": repo_url, "root": root},
        root,
    )
    written: list[Path] = []

    for group_node in tree.children:
        if not group_node.is_group:
            continue

        group_id = group_node.id
        child_skills = group_node.child_skills()
        meta = group_node.meta_skill()

        targets: list[tuple[SkillInfo, str]] = []
        for skill in child_skills:
            targets.append((skill, skill.dir.joinpath("SKILL.md").read_text(encoding="utf-8")))
        if meta:
            targets.append((
                meta,
                render_meta_skill_md(
                    meta,
                    child_skills,
                    base_url=base_url,
                    repo_url=repo_url,
                    group_path=group_id,
                    template=meta_template,
                ),
            ))

        for skill, markdown_text in targets:
            source_path = f"skills/{group_id}/{skill.name}"
            context = {
                "config": config,
                "site": config.site,
                "root": root,
                "base_url": base_url,
                "repo_url": repo_url,
                "nav": nav,
                "skill": {
                    "name": skill.name,
                    # A meta skill is presented as its group's pack, the same
                    # name the index card gives it.
                    "title": (
                        f"{group_node.label} Pack" if skill.is_meta else format_title(skill.name)
                    ),
                    "description": skill.description,
                    "version": skill.version,
                    "status": skill.status,
                    "is_meta": skill.is_meta,
                    # Without a base URL the site is served from wherever it
                    # was unpacked, and this page already sits in the directory
                    # holding the zip.
                    "install_url": (
                        f"{base_url}skills/{group_id}/{skill.name}.skill"
                        if base_url
                        else f"{skill.name}.skill"
                    ),
                    "install_filename": f"{skill.name}.skill",
                    "source_url": f"{repo_url}tree/main/{source_path}" if repo_url else "",
                    "source_path": source_path,
                    "files": package_files(skill),
                    "body_html": render_body_html(markdown_text),
                },
                "group": {"id": group_id, "label": group_node.label},
            }

            dest = config.output_dir / "skills" / group_id / f"{skill.name}.html"
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(template.render(**context), encoding="utf-8")
            written.append(dest)

    return written
