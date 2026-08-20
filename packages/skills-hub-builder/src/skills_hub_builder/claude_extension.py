"""Package a Claude Desktop Extension (.mcpb) from a consumer's templates/mcpb/.

Written to `_site/packages/mcpb/<name>.mcpb` when `outputs.claude_extension`
is true. A .mcpb is a zip whose layout is the extension itself: a
`manifest.json` at the root and whatever the manifest's entry point needs.

The builder ships no extension assets of its own. `templates/mcpb/` in the
consumer project is copied verbatim into the zip, with `{{placeholder}}`
tokens substituted, so the MCP server, its instructions, and the extension's
identity stay with the hub that publishes them. The package filename comes
from the manifest's `name`.
"""

from __future__ import annotations

import json
import time
import zipfile
from pathlib import Path

from .config import HubConfig

PLACEHOLDER_PREFIX = "{{"


def mcpb_template_dir(config: HubConfig) -> Path:
    return config.templates_dir / "mcpb"


def mcpb_package_name(config: HubConfig) -> str:
    """The `name` from templates/mcpb/manifest.json, or "" if there is none."""
    manifest = mcpb_template_dir(config) / "manifest.json"
    if not manifest.is_file():
        return ""
    data = json.loads(manifest.read_text(encoding="utf-8"))
    return data.get("name", "")


def mcpb_download_url(config: HubConfig, base_url: str) -> str:
    """Public URL of the built .mcpb, for template context. "" if not built."""
    if not config.outputs.claude_extension:
        return ""
    name = mcpb_package_name(config)
    if not name:
        return ""
    return f"{base_url}packages/mcpb/{name}.mcpb"


def build_claude_extension(config: HubConfig, *, base_url: str = "") -> Path | None:
    """Render templates/mcpb/ and zip it as _site/packages/mcpb/<name>.mcpb.

    Returns the written path, or None when the project ships no templates/mcpb/.
    """
    template_dir = mcpb_template_dir(config)
    if not template_dir.is_dir():
        print(
            f"outputs.claude_extension is on but {template_dir} does not exist; "
            "no .mcpb written"
        )
        return None

    name = mcpb_package_name(config)
    if not name:
        raise ValueError(
            f"{template_dir / 'manifest.json'} must define a `name`; "
            "it becomes the .mcpb filename."
        )

    sources = [
        p for p in sorted(template_dir.rglob("*")) if p.is_file() and not p.name.startswith(".")
    ]
    texts = {p: p.read_text(encoding="utf-8") for p in sources}
    replacements = _build_replacements(
        config,
        base_url=base_url,
        needs_personas=any("{{personas_" in t for t in texts.values()),
    )

    out_path = config.output_dir / "packages" / "mcpb" / f"{name}.mcpb"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for src in sources:
            content = texts[src]
            if PLACEHOLDER_PREFIX in content:
                content = _render(content, replacements)
            stat = src.stat()
            info = zipfile.ZipInfo(
                str(src.relative_to(template_dir)),
                date_time=time.localtime(stat.st_mtime)[:6],
            )
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (stat.st_mode & 0xFFFF) << 16
            zf.writestr(info, content)

    size_kb = out_path.stat().st_size / 1024
    print(f"Built MCPB: {out_path} ({size_kb:.0f} KB)")
    return out_path


def _build_replacements(
    config: HubConfig,
    *,
    base_url: str,
    needs_personas: bool,
) -> dict[str, str]:
    """Values for the {{…}} tokens the extension templates may use."""
    base = base_url if base_url.endswith("/") or not base_url else base_url + "/"
    replacements = {"base_url": base}

    if not needs_personas:
        return replacements

    personas_path = config.output_dir / "actions" / "personas.json"
    if not personas_path.is_file():
        raise ValueError(
            f"The .mcpb templates reference the persona index but {personas_path} "
            "was not written. Set outputs.gpt_actions: true in hub.yaml."
        )

    personas_text = personas_path.read_text(encoding="utf-8")
    personas = json.loads(personas_text)["personas"]
    replacements["personas_json"] = personas_text
    replacements["personas_summary"] = "\n".join(
        f"- **{p['id']}**: {p['description']} (objective: {p['objective']})" for p in personas
    )
    return replacements


def _render(text: str, replacements: dict[str, str]) -> str:
    for key, value in replacements.items():
        text = text.replace(f"{{{{{key}}}}}", value)
    return text
