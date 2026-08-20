"""Package skills as .skill zip files and generate inventory JSON."""

from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path

from .discover import SkillInfo, SkillNode


def zip_skill(skill: SkillInfo, output_path: Path) -> None:
    """Zip a single skill directory as a .skill file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in sorted(skill.dir.rglob("*")):
            if not file.is_file():
                continue
            arcname = file.relative_to(skill.dir.parent)
            zf.write(file, arcname)


def zip_meta_skill(
    meta_skill: SkillInfo,
    bundled_skills: list[SkillInfo],
    output_path: Path,
    rendered_skill_md: str,
) -> None:
    """Zip a meta skill with bundled skills in references/.

    Bundled skills are placed under <meta-name>/references/<skill-name>/
    so the meta SKILL.md can reference them via relative paths.
    """
    meta_name = meta_skill.name
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{meta_name}/SKILL.md", rendered_skill_md)

        # Include other files from the meta skill dir
        for file in sorted(meta_skill.dir.rglob("*")):
            if not file.is_file() or file.name == "SKILL.md":
                continue
            arcname = file.relative_to(meta_skill.dir.parent)
            zf.write(file, arcname)

        # Bundle child skills
        for skill in bundled_skills:
            for file in sorted(skill.dir.rglob("*")):
                if not file.is_file():
                    continue
                rel = file.relative_to(skill.dir)
                if rel.name == "SKILL.md" and rel.parent == Path("."):
                    rel = Path("subskill.md")
                arcname = Path(meta_name) / "references" / skill.name / rel
                zf.write(file, str(arcname))


def build_bundled_skills_text(skills: list[SkillInfo]) -> str:
    """Generate the bundled skills listing for injection into a meta SKILL.md."""
    lines = []
    for s in skills:
        ref_path = f"references/{s.name}/subskill.md"
        status_label = s.status.capitalize()
        lines.append(
            f"- **{s.name}** (v{s.version}, {status_label}): {s.description}  \n"
            f"  Full instructions: `{ref_path}`"
        )
    return "\n".join(lines)


def parse_meta_sections(text: str) -> dict[str, str]:
    """Split a meta SKILL.md into the sections a wrapper template composes.

    The body is cut at '## Assist Directly': everything before it is `intro`,
    the section itself is `assist_directly`, and any further '## ' sections
    become `extra_sections`.
    """
    m = re.match(r"(---\s*\n.*?\n---)\s*\n(.*)", text, re.DOTALL)
    if not m:
        raise ValueError("Cannot parse meta skill: no YAML frontmatter")
    frontmatter = m.group(1)
    body = m.group(2)

    parts = re.split(r"^## Assist Directly\s*$", body, maxsplit=1, flags=re.MULTILINE)
    intro = parts[0].strip()

    if len(parts) > 1:
        after = parts[1].strip()
        sub = re.split(r"(?=^## )", after, maxsplit=1, flags=re.MULTILINE)
        assist_directly = sub[0].strip()
        extra_sections = sub[1].strip() if len(sub) > 1 else ""
    else:
        assist_directly = ""
        extra_sections = ""

    return {
        "frontmatter": frontmatter,
        "intro": intro,
        "assist_directly": assist_directly,
        "extra_sections": extra_sections,
    }


def render_meta_skill_md(meta_skill: SkillInfo, bundled_skills: list[SkillInfo],
                         *, base_url: str, repo_url: str, group_path: str,
                         template: str | None = None) -> str:
    """Render a meta skill's SKILL.md with bundled skills injected.

    Without a template, the skill's own body is used and its placeholders —
    {{ bundled_skills }} and friends — are substituted in place.

    With a template (a consumer's templates/meta-skill.md), the skill's body is
    split into sections and composed into the template, so every meta skill in
    the hub shares one wrapper and only carries its own distinctive prose.
    """
    text = meta_skill.dir.joinpath("SKILL.md").read_text(encoding="utf-8")

    values: dict[str, str] = {}
    if template is not None:
        values.update(parse_meta_sections(text))
        text = template

    values.update({
        "bundled_skills": build_bundled_skills_text(bundled_skills),
        "hub_url": base_url,
        "inventory_url": f"{base_url}inventory/{group_path}.json",
        "repo_url": repo_url,
        "repo_skills_url": f"{repo_url}tree/main/skills/{group_path}" if repo_url else "",
        "issues_url": f"{repo_url}issues" if repo_url else "",
    })

    for key, value in values.items():
        # Handle both {{ key }} and {{key}} (with and without spaces)
        text = text.replace(f"{{{{ {key} }}}}", value)
        text = text.replace(f"{{{{{key}}}}}", value)

    # Clean up excess blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def build_inventory(tree: SkillNode, base_url: str, repo_url: str = "") -> dict:
    """Generate inventory JSON from the skill tree.

    Produces a groups index (top-level) and per-group inventory files.
    """
    groups_index = []
    inventories = {}

    for group_node in tree.children:
        if not group_node.is_group:
            continue

        group_id = group_node.id
        skills = group_node.child_skills()
        meta = group_node.meta_skill()

        # Build skill entries
        skill_entries = []
        for s in skills:
            skill_entries.append({
                "name": s.name,
                "description": s.description,
                "install_url": f"{base_url}skills/{group_id}/{s.name}.skill",
                "version": s.version,
                "status": s.status,
                "source_path": f"skills/{group_id}/{s.name}",
            })

        meta_entry = None
        if meta:
            meta_entry = {
                "name": meta.name,
                "description": meta.description,
                "install_url": f"{base_url}skills/{group_id}/{meta.name}.skill",
                "version": meta.version,
                "status": meta.status,
                "source_path": f"skills/{group_id}/{meta.name}",
            }

        design = group_node.group.design if group_node.group else {}
        inventory = {
            "group": group_id,
            "label": group_node.label,
            "description": group_node.description,
            "design": design,
            "meta_skill": meta_entry,
            "skills": skill_entries,
        }
        inventories[group_id] = inventory

        groups_index.append({
            "id": group_id,
            "label": group_node.label,
            "description": group_node.description,
            "inventory_url": f"{base_url}inventory/{group_id}.json",
            "meta_skill_url": meta_entry["install_url"] if meta_entry else None,
            "skill_count": len(skill_entries),
        })

    return {
        "groups": {"groups": groups_index, "repo_url": repo_url},
        "inventories": inventories,
    }


def write_inventory(inv_data: dict, output_dir: Path) -> None:
    """Write inventory JSON files to the output directory."""
    inv_dir = output_dir / "inventory"
    inv_dir.mkdir(parents=True, exist_ok=True)

    for group_id, inventory in inv_data["inventories"].items():
        (inv_dir / f"{group_id}.json").write_text(
            json.dumps(inventory, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    (inv_dir / "groups.json").write_text(
        json.dumps(inv_data["groups"], indent=2, ensure_ascii=False), encoding="utf-8"
    )
