"""Load and validate hub.yaml project configuration."""

from __future__ import annotations

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
    )

    actions_raw = raw.get("actions", {})
    actions = ActionsConfig(
        title=actions_raw.get("title", site.title),
        description=actions_raw.get("description", site.subtitle),
    )

    nav = raw.get("nav", [])

    return HubConfig(
        site=site,
        theme=theme,
        outputs=outputs,
        actions=actions,
        nav=nav,
        project_root=project_root.resolve(),
    )
