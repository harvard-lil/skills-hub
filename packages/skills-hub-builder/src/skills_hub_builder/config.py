"""Load and validate hub.yaml project configuration."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class SiteConfig:
    title: str = "Skills Hub"
    subtitle: str = ""
    org_name: str = ""
    org_url: str = ""
    org_parent: str = ""


@dataclass
class ThemeConfig:
    accent_colors: dict[str, str] = field(default_factory=dict)
    exclude: list[str] = field(default_factory=list)


@dataclass
class OutputsConfig:
    site: bool = True
    skill_packages: bool = True
    gpt_actions: bool = False
    claude_extension: bool = False
    suite_bundle: bool = False


@dataclass
class SuiteConfig:
    """Naming for the hub-wide bundle written when outputs.suite_bundle is on.

    The bundle is one plugin holding every skill in the hub. `name` is the
    plugin's identifier (it prefixes each skill in Claude, as `name:skill`)
    and the bundle's filename. `marketplace` names the Claude Code catalog
    that lists it, so the install id is `<name>@<marketplace>`. Both default
    to a slug of the site title. `version` pins the plugin version; left
    empty, the builder derives one from the bundle's contents so that a build
    with unchanged skills publishes an unchanged version.
    """

    name: str = ""
    display_name: str = ""
    description: str = ""
    marketplace: str = ""
    version: str = ""


@dataclass
class ActionsConfig:
    """Naming for the GPT Actions API written when outputs.gpt_actions is on.

    Defaults come from the site block. A hub whose Custom GPT is published
    under a different name than the site can override them under `actions:`.
    """

    title: str = ""
    description: str = ""


@dataclass
class HubConfig:
    """Parsed hub.yaml configuration."""

    site: SiteConfig = field(default_factory=SiteConfig)
    theme: ThemeConfig = field(default_factory=ThemeConfig)
    outputs: OutputsConfig = field(default_factory=OutputsConfig)
    actions: ActionsConfig = field(default_factory=ActionsConfig)
    suite: SuiteConfig = field(default_factory=SuiteConfig)
    nav: list[dict[str, str]] = field(default_factory=list)

    # Resolved paths (set after load)
    project_root: Path = field(default_factory=lambda: Path("."))

    @property
    def skills_dir(self) -> Path:
        return self.project_root / "skills"

    @property
    def website_dir(self) -> Path:
        return self.project_root / "website"

    @property
    def traces_dir(self) -> Path:
        return self.project_root / "traces"

    @property
    def templates_dir(self) -> Path:
        """Consumer-supplied build templates (meta-skill.md, mcpb/)."""
        return self.project_root / "templates"

    @property
    def output_dir(self) -> Path:
        return self.project_root / "_site"


def load_config(project_root: Path) -> HubConfig:
    """Load hub.yaml from the project root, falling back to defaults."""
    config_path = project_root / "hub.yaml"
    raw: dict = {}
    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

    site_raw = raw.get("site", {})
    site = SiteConfig(
        title=site_raw.get("title", "Skills Hub"),
        subtitle=site_raw.get("subtitle", ""),
        org_name=site_raw.get("org_name", site_raw.get("org", "")),
        org_url=site_raw.get("org_url", ""),
        org_parent=site_raw.get("org_parent", ""),
    )

    theme_raw = raw.get("theme", {})
    theme = ThemeConfig(
        accent_colors=theme_raw.get("accent_colors", {}),
        exclude=theme_raw.get("exclude", []),
    )

    outputs_raw = raw.get("outputs", {})
    outputs = OutputsConfig(
        site=outputs_raw.get("site", True),
        skill_packages=outputs_raw.get("skill_packages", True),
        gpt_actions=outputs_raw.get("gpt_actions", False),
        claude_extension=outputs_raw.get("claude_extension", False),
        suite_bundle=outputs_raw.get("suite_bundle", False),
    )

    actions_raw = raw.get("actions", {})
    actions = ActionsConfig(
        title=actions_raw.get("title", site.title),
        description=actions_raw.get("description", site.subtitle),
    )

    suite_raw = raw.get("suite", {}) or {}
    suite_name = suite_raw.get("name") or slugify(site.title)
    suite = SuiteConfig(
        name=suite_name,
        display_name=suite_raw.get("display_name", site.title),
        description=suite_raw.get("description", site.subtitle),
        marketplace=suite_raw.get("marketplace") or suite_name,
        version=str(suite_raw.get("version", "") or ""),
    )

    nav = raw.get("nav", [])

    return HubConfig(
        site=site,
        theme=theme,
        outputs=outputs,
        actions=actions,
        suite=suite,
        nav=nav,
        project_root=project_root.resolve(),
    )


def slugify(text: str) -> str:
    """Lowercase `text` and join its words with single hyphens."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
