"""Package every skill in the hub as one installable bundle.

Written when `outputs.suite_bundle` is true:

- `bundle/<name>.zip`: one plugin directory holding every skill in the hub,
  `<name>/.claude-plugin/plugin.json` plus `<name>/skills/<skill>/...`, and a
  generated `README.md` for the person who opens the zip. claude.ai and the
  Claude desktop app accept it through Customize > Plugins > Upload plugin.
  The `skills/` directories are ordinary Agent Skills directories, so any
  agent can use them as they are.
- `marketplace.json`: a Claude Code plugin marketplace that lists the bundle
  as an `archive` source pinned by sha256. People add it by URL, so
  installing needs access to the published site only, not to the source
  repository.
- `.well-known/agent-skills/index.json`, with one `<skill>.zip` beside it per
  skill: the discovery index that the `skills` CLI reads when given the site
  URL (`npx skills add <site url>`). Its archives hold `SKILL.md` at their
  root, which that CLI requires, unlike the `.skill` zips, which hold a
  top-level `<skill>/` directory.

A skill directly under `skills/`, outside any group, is a hub-level skill:
one that is about the hub as a whole, such as an orientation that routes a
request naming no phase. It is listed first in the bundle and the index, is
also written standalone as `skills/<name>.skill`, and may use the placeholder
`{{ suite_skills }}`, which the build replaces with a listing of every other
skill by group. The listing names skills rather than giving paths, so it
reads the same in the bundle, where the skills sit beside it, and standalone,
where they may not be installed. Hub-level skills get no page or inventory
entry of their own beyond the `suite` block in `inventory/groups.json`.

Meta skills are left out of all three. A meta skill routes among skills that
a one-skill upload cannot register on their own; in a bundle every skill is
registered with its own description, so a router would only duplicate them.

Every zip here is written with fixed timestamps and sorted entries, so an
unchanged skill tree produces byte-identical archives and the sha256 pins and
derived version do not move between builds.
"""

from __future__ import annotations

import hashlib
import json
import zipfile
from dataclasses import dataclass
from pathlib import Path

from .config import HubConfig
from .discover import STATUS_OFFICIAL, SkillInfo, SkillNode
from .packager import packaged_files

#: Schema URL the `skills` CLI checks to select the v0.2.0 index format.
DISCOVERY_SCHEMA = "https://schemas.agentskills.io/discovery/0.2.0/schema.json"
WELL_KNOWN_DIR = Path(".well-known") / "agent-skills"
BUNDLE_DIR = "bundle"
MARKETPLACE_FILE = "marketplace.json"

_ZIP_EPOCH = (1980, 1, 1, 0, 0, 0)


SUITE_SKILLS_PLACEHOLDERS = ("{{ suite_skills }}", "{{suite_skills}}")


@dataclass
class SuiteBundle:
    """What the build wrote, for the install page and the inventory."""

    name: str
    display_name: str
    marketplace: str
    version: str
    skill_count: int
    bundle_path: str
    marketplace_path: str
    skills_index_path: str
    base_url: str
    hub_skills: list[SkillInfo]

    @property
    def install_id(self) -> str:
        return f"{self.name}@{self.marketplace}"

    def url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def inventory_entry(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "skill_count": self.skill_count,
            "bundle_url": self.url(self.bundle_path),
            "marketplace_url": self.url(self.marketplace_path),
            "skills_index_url": self.url(self.skills_index_path),
            "claude_code_install_id": self.install_id,
            "hub_skills": [
                {
                    "name": skill.name,
                    "description": skill.description,
                    "summary": skill.summary or None,
                    "install_url": self.url(f"skills/{skill.name}.skill"),
                    "version": skill.version,
                    "status": skill.status,
                    "source_path": f"skills/{skill.name}",
                }
                for skill in self.hub_skills
            ],
        }


def hub_level_skills(tree: SkillNode) -> list[SkillInfo]:
    """Skills directly under `skills/` that belong to no group."""
    return [
        child.skill
        for child in tree.children
        if child.is_skill and not child.is_group and not child.skill.is_meta
    ]


def suite_skills(tree: SkillNode) -> list[tuple[SkillNode | None, SkillInfo]]:
    """Every non-meta skill in the bundle, paired with its group.

    Hub-level skills come first, paired with None. Group skills follow the
    same one-level walk as skill packaging, so the bundle holds exactly the
    skills that also get standalone `.skill` files. Two skills with one
    `name` would collide in a flat `skills/` directory, so that is an error
    rather than a silent overwrite.
    """
    pairs: list[tuple[SkillNode | None, SkillInfo]] = [
        (None, skill) for skill in hub_level_skills(tree)
    ]
    seen: dict[str, Path] = {skill.name: skill.dir for _g, skill in pairs}
    for group_node in tree.children:
        if not group_node.is_group:
            continue
        for skill in group_node.child_skills():
            if skill.name in seen:
                raise ValueError(
                    f"Skill name {skill.name!r} is used by both {seen[skill.name]} and "
                    f"{skill.dir}; a hub-wide bundle needs every name to be unique."
                )
            seen[skill.name] = skill.dir
            pairs.append((group_node, skill))
    return pairs


def build_suite_bundle(
    tree: SkillNode, config: HubConfig, *, base_url: str = "", repo_url: str = ""
) -> SuiteBundle:
    """Write the bundle, its marketplace, and the skills discovery index."""
    suite = config.suite
    if not suite.name:
        raise ValueError("outputs.suite_bundle needs suite.name or a site.title to derive it from")
    pairs = suite_skills(tree)
    out = config.output_dir

    listing = suite_skills_text(pairs)
    skill_entries: list[tuple[str, bytes]] = []
    for _group, skill in pairs:
        for rel, data in _skill_files(skill, listing):
            skill_entries.append((f"skills/{skill.name}/{rel}", data))
    skill_entries.sort()

    hub_skills = [skill for group, skill in pairs if group is None]
    for skill in hub_skills:
        _write_zip(
            out / "skills" / f"{skill.name}.skill",
            [(f"{skill.name}/{rel}", data) for rel, data in _skill_files(skill, listing)],
        )

    version = suite.version or f"0.0.0+{_content_hash(skill_entries)[:12]}"

    plugin_json = _plugin_manifest(config, pairs, version=version, base_url=base_url,
                                   repo_url=repo_url)
    readme = _bundle_readme(config, pairs, base_url=base_url)
    root = suite.name
    entries = [(f"{root}/{path}", data) for path, data in skill_entries]
    entries.append((f"{root}/.claude-plugin/plugin.json", _json_bytes(plugin_json)))
    entries.append((f"{root}/README.md", readme.encode("utf-8")))

    bundle_path = f"{BUNDLE_DIR}/{suite.name}.zip"
    bundle_bytes = _write_zip(out / bundle_path, entries)

    marketplace = _marketplace(config, pairs, bundle_url=f"{base_url}{bundle_path}",
                               bundle_sha256=hashlib.sha256(bundle_bytes).hexdigest())
    (out / MARKETPLACE_FILE).write_bytes(_json_bytes(marketplace))

    index_path = _write_skills_index(pairs, out / WELL_KNOWN_DIR, listing)

    return SuiteBundle(
        name=suite.name,
        display_name=suite.display_name,
        marketplace=suite.marketplace,
        version=version,
        skill_count=len(pairs),
        bundle_path=bundle_path,
        marketplace_path=MARKETPLACE_FILE,
        skills_index_path=index_path.relative_to(out).as_posix(),
        base_url=base_url,
        hub_skills=hub_skills,
    )


def suite_skills_text(pairs) -> str:
    """The `{{ suite_skills }}` listing: every group skill, by group, by name."""
    lines: list[str] = []
    for group in _groups(pairs):
        lines += [f"**{group.label}**", ""]
        for g, skill in pairs:
            if g is group:
                lines.append(
                    f"- `{skill.name}` (v{skill.version}, {skill.status.capitalize()}): "
                    f"{skill.description}"
                )
        lines.append("")
    return "\n".join(lines).rstrip()


def _skill_files(skill: SkillInfo, listing: str) -> list[tuple[str, bytes]]:
    """A skill's packaged files, with a hub-level SKILL.md's listing filled in."""
    files = []
    for file in packaged_files(skill.dir):
        rel = file.relative_to(skill.dir).as_posix()
        data = file.read_bytes()
        if rel == "SKILL.md":
            text = data.decode("utf-8")
            for placeholder in SUITE_SKILLS_PLACEHOLDERS:
                text = text.replace(placeholder, listing)
            data = text.encode("utf-8")
        files.append((rel, data))
    return files


def _plugin_manifest(config: HubConfig, pairs, *, version: str, base_url: str,
                     repo_url: str) -> dict:
    suite = config.suite
    manifest: dict = {
        "name": suite.name,
        "displayName": suite.display_name,
        "version": version,
        "description": suite.description or suite.display_name,
        "author": _owner(config),
        "keywords": [group.id for group in _groups(pairs)],
    }
    # Claude Code refuses to load a plugin whose `homepage` does not parse
    # as a URL, so a local build with no --base-url leaves it out.
    if base_url.startswith(("https://", "http://")):
        manifest["homepage"] = base_url
    if repo_url:
        manifest["repository"] = repo_url
    return manifest


def _marketplace(config: HubConfig, pairs, *, bundle_url: str, bundle_sha256: str) -> dict:
    suite = config.suite
    return {
        "name": suite.marketplace,
        "owner": _owner(config),
        "description": config.site.subtitle or config.site.title,
        "plugins": [
            {
                "name": suite.name,
                "displayName": suite.display_name,
                "description": suite.description or suite.display_name,
                "source": {"source": "archive", "url": bundle_url, "sha256": bundle_sha256},
                "keywords": [group.id for group in _groups(pairs)],
            }
        ],
    }


def _write_skills_index(pairs, index_dir: Path, listing: str) -> Path:
    entries = []
    for _group, skill in pairs:
        data = _write_zip(index_dir / f"{skill.name}.zip", _skill_files(skill, listing))
        entries.append({
            "name": skill.name,
            "type": "archive",
            "description": skill.description,
            "url": f"{skill.name}.zip",
            "digest": f"sha256:{hashlib.sha256(data).hexdigest()}",
        })
    index_path = index_dir / "index.json"
    index_path.write_bytes(_json_bytes({"$schema": DISCOVERY_SCHEMA, "skills": entries}))
    return index_path


def _bundle_readme(config: HubConfig, pairs, *, base_url: str) -> str:
    suite = config.suite
    lines = [f"# {suite.display_name}", ""]
    if suite.description:
        lines += [suite.description, ""]
    lines += [
        (
            f"This bundle holds all {len(pairs)} skills from {config.site.title}. "
            "Each folder under `skills/` is one skill: `SKILL.md` is the instructions "
            "your agent follows, and `README.md`, where present, is a guide for you."
        ),
        "",
    ]
    if base_url:
        lines += [
            f"Install instructions: {base_url}install.html",
            "",
            "In Claude Code (2.1.275 or later), one command adds the marketplace and installs this bundle:",
            "",
            "```",
            f"/plugin install {suite.name} --marketplace {base_url}{MARKETPLACE_FILE}",
            "```",
            "",
        ]
    drafts = [skill.name for _g, skill in pairs if skill.status != STATUS_OFFICIAL]
    if len(drafts) == len(pairs):
        lines += [
            "Every skill here is a draft: none has yet been reviewed and marked official.",
            "",
        ]
    elif drafts:
        official = [skill.name for _g, skill in pairs if skill.status == STATUS_OFFICIAL]
        lines += [
            "Reviewed and official: " + ", ".join(f"`{name}`" for name in official) + ".",
            "",
            "Drafts, not yet reviewed: " + ", ".join(f"`{name}`" for name in drafts) + ".",
            "",
        ]
    hub_skills = [skill for group, skill in pairs if group is None]
    if hub_skills:
        lines += ["## Hub-wide", ""]
        for skill in hub_skills:
            lines.append(f"- `{skill.name}`: {skill.summary or skill.description}")
        lines.append("")
    for group in _groups(pairs):
        lines += [f"## {group.label}", ""]
        if group.description:
            lines += [group.description, ""]
        for g, skill in pairs:
            if g is group:
                lines.append(f"- `{skill.name}`: {skill.summary or skill.description}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _groups(pairs) -> list[SkillNode]:
    groups: list[SkillNode] = []
    for group, _skill in pairs:
        if group is not None and group not in groups:
            groups.append(group)
    return groups


def _owner(config: HubConfig) -> dict:
    """The publishing organization, named as the site footer names it.

    `org_url` belongs to `org_name` in hub.yaml, so the pair is kept together;
    `org_parent` stands in only when there is no `org_name`.
    """
    site = config.site
    owner = {"name": site.org_name or site.org_parent or config.suite.display_name}
    if site.org_url and site.org_name:
        owner["url"] = site.org_url
    return owner


def _content_hash(entries: list[tuple[str, bytes]]) -> str:
    digest = hashlib.sha256()
    for path, data in entries:
        digest.update(path.encode("utf-8") + b"\0")
        digest.update(hashlib.sha256(data).digest())
    return digest.hexdigest()


def _json_bytes(data: dict) -> bytes:
    return (json.dumps(data, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def _write_zip(path: Path, entries: list[tuple[str, bytes]]) -> bytes:
    """Write `entries` as a reproducible zip and return the archive's bytes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        for arcname, data in sorted(entries):
            info = zipfile.ZipInfo(arcname, date_time=_ZIP_EPOCH)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, data)
    return path.read_bytes()
