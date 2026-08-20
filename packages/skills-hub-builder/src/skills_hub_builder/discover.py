"""Discover skills and groups from the filesystem.

The skills/ directory is walked recursively. Any directory containing a
group.yaml is a group. Any directory containing a SKILL.md is a skill.
A directory can be both (a group with its own meta-skill).

The result is a tree of SkillNode objects representing the full hierarchy.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class SkillInfo:
    """A single skill parsed from a SKILL.md file."""

    name: str
    description: str
    version: str = "0.0.0"
    status: str = "preview"
    dir: Path = field(default_factory=lambda: Path("."))
    frontmatter: dict[str, str] = field(default_factory=dict)

    @property
    def is_meta(self) -> bool:
        return self.name.endswith("-meta")


@dataclass
class GroupInfo:
    """Metadata from a group.yaml file."""

    label: str = ""
    description: str = ""
    design: dict[str, Any] = field(default_factory=dict)
    accent_color: str = ""
    order: int | None = None


@dataclass
class SkillNode:
    """A node in the skill tree. Can be a group, a skill, or both."""

    id: str
    path: Path
    group: GroupInfo | None = None
    skill: SkillInfo | None = None
    children: list[SkillNode] = field(default_factory=list)

    @property
    def is_group(self) -> bool:
        return self.group is not None or len(self.children) > 0

    @property
    def is_skill(self) -> bool:
        return self.skill is not None

    @property
    def label(self) -> str:
        if self.group and self.group.label:
            return self.group.label
        return self.id.replace("-", " ").title()

    @property
    def description(self) -> str:
        if self.group:
            return self.group.description
        if self.skill:
            return self.skill.description
        return ""

    def all_skills(self) -> list[SkillInfo]:
        """Return all skills in this node and its descendants (flat)."""
        result = []
        if self.skill and not self.skill.is_meta:
            result.append(self.skill)
        for child in self.children:
            result.extend(child.all_skills())
        return result

    def meta_skill(self) -> SkillInfo | None:
        """Return the meta skill for this group, if any.

        Checks both the group's own SKILL.md and direct children whose name
        ends with -meta.
        """
        if self.skill and self.skill.is_meta:
            return self.skill
        for child in self.children:
            if child.skill and child.skill.is_meta:
                return child.skill
        return None

    def child_skills(self) -> list[SkillInfo]:
        """Return direct child skills (non-meta, non-group children)."""
        result = []
        for child in self.children:
            if child.is_skill and not child.is_group and not child.skill.is_meta:
                result.append(child.skill)
        return result


def parse_frontmatter(path: Path) -> dict[str, str]:
    """Extract YAML frontmatter from a SKILL.md file."""
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not m:
        raise ValueError(f"No YAML frontmatter in {path}")
    result = {}
    for line in m.group(1).strip().splitlines():
        key, sep, val = line.partition(":")
        if sep:
            k = key.strip()
            v = val.strip()
            # Skip nested keys like 'metadata:'
            if v or k == "metadata":
                result[k] = v
    return result


def load_group_yaml(path: Path) -> GroupInfo:
    """Load a group.yaml file."""
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    return GroupInfo(
        label=raw.get("label", ""),
        description=raw.get("description", ""),
        design=raw.get("design", {}),
        accent_color=raw.get("accent_color", ""),
        order=raw.get("order"),
    )


def discover_tree(skills_dir: Path) -> SkillNode:
    """Walk skills_dir and build the skill tree.

    Returns the root node representing the skills/ directory itself.
    """
    return _discover_node(skills_dir, skills_dir.name)


def _discover_node(path: Path, node_id: str) -> SkillNode:
    """Recursively discover a single node (directory) in the skill tree."""
    node = SkillNode(id=node_id, path=path)

    # Check for group.yaml
    group_path = path / "group.yaml"
    if group_path.exists():
        node.group = load_group_yaml(group_path)

    # Check for SKILL.md
    skill_path = path / "SKILL.md"
    if skill_path.exists():
        fm = parse_frontmatter(skill_path)
        node.skill = SkillInfo(
            name=fm.get("name", node_id),
            description=fm.get("description", ""),
            version=fm.get("version", "0.0.0"),
            status=fm.get("status", "preview"),
            dir=path,
            frontmatter=fm,
        )

    # Discover children (subdirectories that contain either group.yaml or SKILL.md)
    if path.is_dir():
        for child_dir in sorted(path.iterdir()):
            if not child_dir.is_dir():
                continue
            if child_dir.name.startswith(".") or child_dir.name.startswith("_"):
                continue
            # Only include if it has relevant content somewhere inside
            if _has_skill_content(child_dir):
                child_node = _discover_node(child_dir, child_dir.name)
                node.children.append(child_node)

    # Children with an explicit group.yaml `order` come first (ascending);
    # everything else stays alphabetical after them.
    node.children.sort(
        key=lambda c: (
            c.group.order if c.group and c.group.order is not None else float("inf"),
            c.id,
        )
    )

    return node


def _has_skill_content(path: Path) -> bool:
    """Check if a directory contains skill content (SKILL.md or group.yaml), recursively."""
    if (path / "SKILL.md").exists() or (path / "group.yaml").exists():
        return True
    for child in path.iterdir():
        if child.is_dir() and not child.name.startswith("."):
            if _has_skill_content(child):
                return True
    return False
