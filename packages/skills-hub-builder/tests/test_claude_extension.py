"""Tests for the Claude Desktop Extension output (outputs.claude_extension)."""

import json
import zipfile
from pathlib import Path

import pytest
from skills_hub_builder.build import build
from skills_hub_builder.claude_extension import (
    build_claude_extension,
    mcpb_download_url,
)
from skills_hub_builder.config import load_config


def _write_hub_yaml(project: Path, *, gpt_actions: bool = True) -> None:
    (project / "hub.yaml").write_text(
        "site:\n"
        "  title: Test Hub\n"
        "outputs:\n"
        f"  gpt_actions: {str(gpt_actions).lower()}\n"
        "  claude_extension: true\n",
        encoding="utf-8",
    )


def _write_templates(project: Path, *, server_text: str = "Base is {{base_url}}\n") -> Path:
    mcpb = project / "templates" / "mcpb"
    (mcpb / "server").mkdir(parents=True)
    (mcpb / "manifest.json").write_text(
        json.dumps({"manifest_version": "0.1", "name": "test-hub", "version": "0.1.0"}, indent=2),
        encoding="utf-8",
    )
    (mcpb / "server" / "index.js").write_text("// server\n", encoding="utf-8")
    (mcpb / "server" / "instructions.md").write_text(server_text, encoding="utf-8")
    return mcpb


def test_no_extension_without_templates(tmp_project: Path, capsys):
    """A hub that turns the flag on but ships no templates gets a message, not a crash."""
    _write_hub_yaml(tmp_project)
    build(tmp_project, base_url="https://example.com/")

    assert not (tmp_project / "_site" / "packages").exists()
    assert "no .mcpb written" in capsys.readouterr().out


def test_extension_is_zipped_from_templates(tmp_project: Path):
    _write_templates(tmp_project)
    _write_hub_yaml(tmp_project)

    build(tmp_project, base_url="https://example.com/")

    mcpb = tmp_project / "_site" / "packages" / "mcpb" / "test-hub.mcpb"
    assert mcpb.is_file()
    with zipfile.ZipFile(mcpb) as zf:
        assert zf.namelist() == [
            "manifest.json",
            "server/index.js",
            "server/instructions.md",
        ]
        assert zf.read("server/instructions.md").decode() == "Base is https://example.com/\n"


def test_package_name_comes_from_the_manifest(tmp_project: Path):
    mcpb = _write_templates(tmp_project)
    (mcpb / "manifest.json").write_text(
        json.dumps({"manifest_version": "0.1", "name": "renamed-pack"}), encoding="utf-8"
    )
    _write_hub_yaml(tmp_project)

    build(tmp_project, base_url="https://example.com/")

    assert (tmp_project / "_site" / "packages" / "mcpb" / "renamed-pack.mcpb").is_file()


def test_manifest_without_a_name_is_an_error(tmp_project: Path):
    mcpb = _write_templates(tmp_project)
    (mcpb / "manifest.json").write_text(json.dumps({"manifest_version": "0.1"}), encoding="utf-8")
    _write_hub_yaml(tmp_project)

    config = load_config(tmp_project)
    config.output_dir.mkdir(parents=True, exist_ok=True)
    with pytest.raises(ValueError, match="must define a `name`"):
        build_claude_extension(config, base_url="https://example.com/")


def test_persona_placeholders_are_filled_from_the_actions_index(tmp_project: Path):
    _write_templates(
        tmp_project,
        server_text="Personas:\n{{personas_summary}}\n\nRaw:\n{{personas_json}}\n",
    )
    _write_hub_yaml(tmp_project)

    build(tmp_project, base_url="https://example.com/")

    mcpb = tmp_project / "_site" / "packages" / "mcpb" / "test-hub.mcpb"
    with zipfile.ZipFile(mcpb) as zf:
        text = zf.read("server/instructions.md").decode()
    assert "- **analysis**: Routes analysis tasks (objective: Help with analysis)" in text
    assert '"id": "analysis"' in text


def test_persona_placeholders_require_gpt_actions(tmp_project: Path):
    _write_templates(tmp_project, server_text="{{personas_summary}}\n")
    _write_hub_yaml(tmp_project, gpt_actions=False)

    with pytest.raises(ValueError, match="outputs.gpt_actions"):
        build(tmp_project, base_url="https://example.com/")


def test_download_url_reaches_the_templates(tmp_project: Path):
    _write_templates(tmp_project)
    _write_hub_yaml(tmp_project)
    website = tmp_project / "website"
    website.mkdir()
    (website / "install.html").write_text(
        "<a href=\"{{ mcpb_download_url }}\">get it</a>", encoding="utf-8"
    )

    build(tmp_project, base_url="https://example.com/")

    html = (tmp_project / "_site" / "install.html").read_text()
    assert 'href="https://example.com/packages/mcpb/test-hub.mcpb"' in html


def test_download_url_is_empty_when_the_flag_is_off(tmp_project: Path):
    _write_templates(tmp_project)
    (tmp_project / "hub.yaml").write_text(
        "site:\n  title: Test Hub\noutputs:\n  claude_extension: false\n", encoding="utf-8"
    )

    config = load_config(tmp_project)
    assert mcpb_download_url(config, "https://example.com/") == ""


def test_extension_zip_is_reproducible(tmp_project: Path):
    """Entry timestamps come from the template files, so rebuilds are identical."""
    _write_templates(tmp_project)
    _write_hub_yaml(tmp_project)

    build(tmp_project, base_url="https://example.com/")
    first = (tmp_project / "_site" / "packages" / "mcpb" / "test-hub.mcpb").read_bytes()
    build(tmp_project, base_url="https://example.com/")
    second = (tmp_project / "_site" / "packages" / "mcpb" / "test-hub.mcpb").read_bytes()

    assert first == second
