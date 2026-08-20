"""Render the skill tree as GPT Actions: static JSON endpoints plus an OpenAPI spec.

Written to `_site/actions/` when `outputs.gpt_actions` is true. A ChatGPT
Custom GPT points its Action at the OpenAPI spec and then progressively
fetches the JSON files as ordinary GETs, so nothing here needs a server.

Endpoint layout:

  GET /actions/personas.json
      Index: id, label, description, objective, skill_count per group.

  GET /actions/personas/{persona_id}.json
      One group's design block plus its skills with descriptions.

  GET /actions/skills/{persona_id}/{skill_name}.json
      The full SKILL.md body for one skill, plus its reference list.

  GET /actions/skills/{persona_id}/{skill_name}/references/{ref_name}.json
      One reference markdown document shipped alongside a skill.

`persona` is the wire vocabulary of this API, kept because published Custom
GPTs and .mcpb extensions already call these paths. It names the same thing
the rest of the builder calls a group.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .config import HubConfig
from .discover import SkillNode


def build_gpt_actions(
    tree: SkillNode,
    config: HubConfig,
    *,
    base_url: str = "",
) -> None:
    """Write every GPT Actions file for the discovered tree."""
    actions_dir = config.output_dir / "actions"
    actions_dir.mkdir(parents=True, exist_ok=True)

    groups = [c for c in tree.children if c.is_group]
    title = config.actions.title
    description = config.actions.description

    # 1. Group index
    index_entries = []
    for group in groups:
        meta = group.meta_skill()
        design = group.group.design if group.group else {}
        index_entries.append(
            {
                "id": group.id,
                "label": group.label,
                "description": meta.description if meta else "",
                "objective": design.get("objective", ""),
                "skill_count": len(group.child_skills()),
            }
        )

    _write_json(
        actions_dir / "personas.json",
        {
            "personas": index_entries,
            "description": (
                f"{title} persona index. Each persona targets a specific "
                "type of user and educational objective. Read the description and "
                "objective fields to decide which persona matches the user's needs, "
                "then fetch full detail at /actions/personas/{id}.json."
            ),
        },
    )

    # 2. Per-group detail
    personas_out = actions_dir / "personas"
    personas_out.mkdir(parents=True, exist_ok=True)

    for group in groups:
        design = group.group.design if group.group else {}
        skills_summary = []
        for s in group.child_skills():
            refs = discover_references(s.dir)
            skills_summary.append(
                {
                    "name": s.name,
                    "description": s.description,
                    "version": s.version,
                    "status": s.status,
                    "has_references": len(refs) > 0,
                    "reference_count": len(refs),
                }
            )

        _write_json(
            personas_out / f"{group.id}.json",
            {
                "id": group.id,
                "label": group.label,
                "headline": group.description,
                "pitch": design.get("pitch", ""),
                "design": design,
                "skills": skills_summary,
                "usage_hint": (
                    "Pick a skill by name, then fetch its full instructions at "
                    f"/actions/skills/{group.id}/{{skill_name}}."
                ),
            },
        )

    # 3. Per-skill full content
    skills_out = actions_dir / "skills"

    for group in groups:
        group_out = skills_out / group.id
        group_out.mkdir(parents=True, exist_ok=True)

        for s in group.child_skills():
            body = read_skill_body(s.dir / "SKILL.md")
            refs = discover_references(s.dir)
            ref_entries = [
                {
                    "name": r["name"],
                    "fetch_path": f"/actions/skills/{group.id}/{s.name}/references/{r['name']}",
                }
                for r in refs
            ]

            _write_json(
                group_out / f"{s.name}.json",
                {
                    "name": s.name,
                    "description": s.description,
                    "version": s.version,
                    "status": s.status,
                    "persona": group.id,
                    "skill_body": body,
                    "references": ref_entries,
                    "usage_hint": (
                        "The skill_body field contains the full skill instructions. "
                        "Follow them to assist the user. "
                        "If references are listed, fetch them as needed for additional context."
                    )
                    if ref_entries
                    else (
                        "The skill_body field contains the full skill instructions. "
                        "Follow them to assist the user."
                    ),
                },
            )

    # 4. Reference documents, mirroring the on-disk layout
    for group in groups:
        for s in group.child_skills():
            refs = discover_references(s.dir)
            if not refs:
                continue
            ref_dir_out = skills_out / group.id / s.name / "references"
            ref_dir_out.mkdir(parents=True, exist_ok=True)
            for r in refs:
                content = (s.dir / "references" / r["filename"]).read_text(encoding="utf-8")
                _write_json(
                    ref_dir_out / f"{r['name']}.json",
                    {
                        "name": r["name"],
                        "skill": s.name,
                        "persona": group.id,
                        "content": content,
                    },
                )

    # 5. OpenAPI spec, in both serializations
    spec = build_openapi_spec(groups, base_url, title=title, description=description)
    _write_json(actions_dir / "openapi.json", spec)
    _write_openapi_yaml(actions_dir / "openapi.yaml", spec)

    skill_count = sum(len(g.child_skills()) for g in groups)
    print(f"Built GPT Actions: {len(groups)} personas, {skill_count} skills")
    print(f"OpenAPI spec: {actions_dir / 'openapi.json'}")


def read_skill_body(path: Path) -> str:
    """Return a SKILL.md's body — everything after the YAML frontmatter."""
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)", text, re.DOTALL)
    if not m:
        raise ValueError(f"No YAML frontmatter in {path}")
    return m.group(2).strip()


def discover_references(skill_dir: Path) -> list[dict[str, str]]:
    """List the markdown files in a skill's references/ subdirectory."""
    refs_dir = skill_dir / "references"
    if not refs_dir.is_dir():
        return []
    return [
        {"name": f.stem, "filename": f.name}
        for f in sorted(refs_dir.iterdir())
        if f.suffix == ".md" and f.is_file()
    ]


def build_openapi_spec(
    groups: list[SkillNode],
    base_url: str,
    *,
    title: str,
    description: str,
) -> dict[str, Any]:
    """Build the OpenAPI 3.1 spec describing the action endpoints."""
    persona_ids = [g.id for g in groups]
    skill_names: set[str] = set()
    ref_names: set[str] = set()

    for g in groups:
        for s in g.child_skills():
            skill_names.add(s.name)
            for r in discover_references(s.dir):
                ref_names.add(r["name"])

    server_url = base_url.rstrip("/") if base_url else "https://example.github.io/skills-hub-demo"

    return {
        "openapi": "3.1.0",
        "info": {
            "title": title,
            "description": description,
            "version": "1.0.0",
        },
        "servers": [{"url": server_url}],
        "paths": {
            "/actions/personas.json": {
                "get": {
                    "operationId": "listPersonas",
                    "summary": "List all available personas",
                    "description": (
                        f"Returns a lightweight index of all personas in the {title}. "
                        "Each entry includes the persona id, display label, headline, and number of skills. "
                        "Use a persona id to fetch its full detail."
                    ),
                    "responses": {
                        "200": {
                            "description": "Persona index",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/PersonaIndex",
                                    }
                                }
                            },
                        },
                    },
                },
            },
            "/actions/personas/{persona_id}.json": {
                "get": {
                    "operationId": "getPersona",
                    "summary": "Get full detail for one persona",
                    "description": (
                        "Returns a persona's design principles, pedagogical objective, tone, "
                        "and a list of available skills with descriptions. Use a skill name "
                        "to fetch its full instructions."
                    ),
                    "parameters": [_persona_id_param(persona_ids)],
                    "responses": {
                        "200": {
                            "description": "Persona detail with skill listing",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/PersonaDetail",
                                    }
                                }
                            },
                        },
                    },
                },
            },
            "/actions/skills/{persona_id}/{skill_name}.json": {
                "get": {
                    "operationId": "getSkill",
                    "summary": "Get full skill instructions",
                    "description": (
                        "Returns the complete skill instructions (the SKILL.md body) for one skill, "
                        "plus metadata and a list of available reference documents. "
                        "Follow the skill_body instructions to assist the user."
                    ),
                    "parameters": [
                        _persona_id_param(persona_ids),
                        _skill_name_param(skill_names),
                    ],
                    "responses": {
                        "200": {
                            "description": "Full skill content",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/SkillDetail",
                                    }
                                }
                            },
                        },
                    },
                },
            },
            "/actions/skills/{persona_id}/{skill_name}/references/{ref_name}.json": {
                "get": {
                    "operationId": "getReference",
                    "summary": "Get a skill's reference document",
                    "description": (
                        "Returns the content of a reference markdown document that accompanies a skill. "
                        "Only fetch when the skill instructions direct you to."
                    ),
                    "parameters": [
                        _persona_id_param(persona_ids),
                        _skill_name_param(skill_names),
                        _ref_name_param(ref_names),
                    ],
                    "responses": {
                        "200": {
                            "description": "Reference document content",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/ReferenceDetail",
                                    }
                                }
                            },
                        },
                    },
                },
            },
        },
        "components": {
            "schemas": {
                "PersonaIndex": {
                    "type": "object",
                    "properties": {
                        "description": {"type": "string"},
                        "personas": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {
                                        "type": "string",
                                        "description": "Persona identifier",
                                    },
                                    "label": {
                                        "type": "string",
                                        "description": "Display name",
                                    },
                                    "description": {
                                        "type": "string",
                                        "description": (
                                            "When this persona applies: describes the type of user and "
                                            "tasks this persona handles. Use this to match against the "
                                            "user's question."
                                        ),
                                    },
                                    "objective": {
                                        "type": "string",
                                        "description": "The persona's core pedagogical objective and constraint",
                                    },
                                    "skill_count": {
                                        "type": "integer",
                                        "description": "Number of available skills",
                                    },
                                },
                            },
                        },
                    },
                },
                "PersonaDetail": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "label": {"type": "string"},
                        "headline": {"type": "string"},
                        "pitch": {"type": "string"},
                        "design": {
                            "type": "object",
                            "description": "Pedagogical design: objective, principles, tone, success criteria",
                            "properties": {
                                "objective": {"type": "string"},
                                "principles": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                                "tone": {"type": "string"},
                                "success": {"type": "string"},
                            },
                        },
                        "skills": {
                            "type": "array",
                            "description": "Available skills — fetch one by name to get full instructions",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "description": {"type": "string"},
                                    "version": {"type": "string"},
                                    "status": {
                                        "type": "string",
                                        "enum": ["preview", "official"],
                                        "description": "Release status of the skill",
                                    },
                                    "has_references": {"type": "boolean"},
                                    "reference_count": {"type": "integer"},
                                },
                            },
                        },
                        "usage_hint": {"type": "string"},
                    },
                },
                "SkillDetail": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "description": {"type": "string"},
                        "version": {"type": "string"},
                        "status": {
                            "type": "string",
                            "enum": ["preview", "official"],
                            "description": "Release status of the skill",
                        },
                        "persona": {"type": "string"},
                        "skill_body": {
                            "type": "string",
                            "description": "Complete skill instructions in markdown. Follow these to assist the user.",
                        },
                        "references": {
                            "type": "array",
                            "description": "Reference documents available for this skill",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "fetch_path": {
                                        "type": "string",
                                        "description": "Path to fetch reference content",
                                    },
                                },
                            },
                        },
                        "usage_hint": {"type": "string"},
                    },
                },
                "ReferenceDetail": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "skill": {"type": "string"},
                        "persona": {"type": "string"},
                        "content": {
                            "type": "string",
                            "description": "Full markdown content of the reference document",
                        },
                    },
                },
            },
        },
    }


def _persona_id_param(persona_ids: list[str]) -> dict[str, Any]:
    return {
        "name": "persona_id",
        "in": "path",
        "required": True,
        "schema": {"type": "string", "enum": persona_ids},
        "description": "Persona identifier",
    }


def _skill_name_param(skill_names: set[str]) -> dict[str, Any]:
    return {
        "name": "skill_name",
        "in": "path",
        "required": True,
        "schema": {"type": "string", "enum": sorted(skill_names)},
        "description": "Skill name (unique within a persona)",
    }


def _ref_name_param(ref_names: set[str]) -> dict[str, Any]:
    flat = sorted(ref_names)
    return {
        "name": "ref_name",
        "in": "path",
        "required": True,
        "schema": {"type": "string", "enum": flat} if flat else {"type": "string"},
        "description": "Reference document name (without .md extension)",
    }


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _write_openapi_yaml(path: Path, spec: dict[str, Any]) -> None:
    """Write the same spec as YAML, which is what people read."""
    import yaml

    path.write_text(
        yaml.dump(spec, default_flow_style=False, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
