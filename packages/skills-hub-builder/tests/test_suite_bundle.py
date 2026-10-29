"""Tests for the hub-wide bundle (outputs.suite_bundle)."""

import hashlib
import json
import zipfile
from pathlib import Path

import pytest
from skills_hub_builder.build import build
from skills_hub_builder.config import load_config

BASE = "https://example.com/hub/"


def _enable(project: Path, extra: str = "") -> None:
    hub = project / "hub.yaml"
    hub.write_text(
        hub.read_text(encoding="utf-8") + "outputs:\n  suite_bundle: true\n" + extra,
        encoding="utf-8",
    )


def _hub_skill(project: Path) -> None:
    sk = project / "skills" / "test-hub-guide"
    (sk / "_hub").mkdir(parents=True)
    (sk / "SKILL.md").write_text(
        "---\nname: test-hub-guide\ndescription: Orients a request that names no tool\n"
        "version: 0.1.0\nstatus: draft\n---\n\n# Guide\n\n{{ suite_skills }}\n",
        encoding="utf-8",
    )
    (sk / "_hub" / "metadata.yaml").write_text("summary: Where to start\n", encoding="utf-8")


def test_off_by_default(tmp_project: Path):
    build(tmp_project, base_url=BASE)
    site = tmp_project / "_site"
    assert not (site / "bundle").exists()
    assert not (site / "marketplace.json").exists()
    assert not (site / ".well-known").exists()
    assert "suite" not in json.loads((site / "inventory" / "groups.json").read_text())


def test_suite_defaults_from_site_title(tmp_project: Path):
    config = load_config(tmp_project)
    assert config.suite.name == "test-hub"
    assert config.suite.marketplace == "test-hub"
    assert config.suite.display_name == "Test Hub"


def test_bundle_is_a_plugin_of_every_non_meta_skill(tmp_project: Path):
    _enable(tmp_project)
    build(tmp_project, base_url=BASE, repo_url="https://github.com/org/repo/")
    bundle = tmp_project / "_site" / "bundle" / "test-hub.zip"
    with zipfile.ZipFile(bundle) as zf:
        names = set(zf.namelist())
        manifest = json.loads(zf.read("test-hub/.claude-plugin/plugin.json"))
        readme = zf.read("test-hub/README.md").decode()
    assert "test-hub/skills/data-check/SKILL.md" in names
    assert "test-hub/skills/watch-feeds/SKILL.md" in names
    assert not any("analysis-meta" in n for n in names)
    assert manifest["name"] == "test-hub"
    assert manifest["homepage"] == BASE
    assert manifest["version"].startswith("0.0.0+")
    assert "`data-check`" in readme and "## Analysis Tools" in readme
    assert "Reviewed and official: `data-check`." in readme
    assert "Drafts, not yet reviewed: `watch-feeds`." in readme


def test_marketplace_pins_the_bundle(tmp_project: Path):
    _enable(tmp_project, "suite:\n  name: everything\n  marketplace: test-catalog\n")
    build(tmp_project, base_url=BASE)
    site = tmp_project / "_site"
    market = json.loads((site / "marketplace.json").read_text())
    assert market["name"] == "test-catalog"
    (entry,) = market["plugins"]
    assert entry["name"] == "everything"
    assert entry["source"]["source"] == "archive"
    assert entry["source"]["url"] == f"{BASE}bundle/everything.zip"
    digest = hashlib.sha256((site / "bundle" / "everything.zip").read_bytes()).hexdigest()
    assert entry["source"]["sha256"] == digest
    suite = json.loads((site / "inventory" / "groups.json").read_text())["suite"]
    assert suite["claude_code_install_id"] == "everything@test-catalog"
    assert suite["skill_count"] == 2


def test_skills_index_archives_have_root_skill_md(tmp_project: Path):
    _enable(tmp_project)
    build(tmp_project, base_url=BASE)
    wk = tmp_project / "_site" / ".well-known" / "agent-skills"
    index = json.loads((wk / "index.json").read_text())
    assert index["$schema"].endswith("/discovery/0.2.0/schema.json")
    by_name = {e["name"]: e for e in index["skills"]}
    assert set(by_name) == {"data-check", "watch-feeds"}
    entry = by_name["data-check"]
    data = (wk / entry["url"]).read_bytes()
    assert entry["digest"] == f"sha256:{hashlib.sha256(data).hexdigest()}"
    with zipfile.ZipFile(wk / entry["url"]) as zf:
        assert "SKILL.md" in zf.namelist()


def test_bundle_bytes_are_reproducible(tmp_project: Path):
    _enable(tmp_project)
    build(tmp_project, base_url=BASE)
    first = (tmp_project / "_site" / "bundle" / "test-hub.zip").read_bytes()
    for md in (tmp_project / "skills").rglob("SKILL.md"):
        md.touch()
    build(tmp_project, base_url=BASE)
    assert (tmp_project / "_site" / "bundle" / "test-hub.zip").read_bytes() == first


def test_version_follows_content(tmp_project: Path):
    _enable(tmp_project)
    build(tmp_project, base_url=BASE)
    market = tmp_project / "_site" / "inventory" / "groups.json"
    before = json.loads(market.read_text())["suite"]["version"]
    md = tmp_project / "skills" / "analysis" / "data-check" / "SKILL.md"
    md.write_text(md.read_text() + "\nMore.\n", encoding="utf-8")
    build(tmp_project, base_url=BASE)
    assert json.loads(market.read_text())["suite"]["version"] != before


def test_pinned_version_is_used(tmp_project: Path):
    _enable(tmp_project, "suite:\n  version: 2.0.0\n")
    build(tmp_project, base_url=BASE)
    with zipfile.ZipFile(tmp_project / "_site" / "bundle" / "test-hub.zip") as zf:
        assert json.loads(zf.read("test-hub/.claude-plugin/plugin.json"))["version"] == "2.0.0"


def test_local_build_omits_homepage(tmp_project: Path):
    _enable(tmp_project)
    build(tmp_project)
    with zipfile.ZipFile(tmp_project / "_site" / "bundle" / "test-hub.zip") as zf:
        assert "homepage" not in json.loads(zf.read("test-hub/.claude-plugin/plugin.json"))


def test_duplicate_skill_names_fail(tmp_project: Path):
    _enable(tmp_project)
    dup = tmp_project / "skills" / "monitoring" / "data-check-copy"
    dup.mkdir()
    (dup / "SKILL.md").write_text(
        "---\nname: data-check\ndescription: Same name\n---\n", encoding="utf-8"
    )
    with pytest.raises(ValueError, match="data-check"):
        build(tmp_project, base_url=BASE)


def test_hub_level_skill_is_bundled_first_and_listed(tmp_project: Path):
    _enable(tmp_project)
    _hub_skill(tmp_project)
    build(tmp_project, base_url=BASE)
    site = tmp_project / "_site"
    with zipfile.ZipFile(site / "bundle" / "test-hub.zip") as zf:
        guide = zf.read("test-hub/skills/test-hub-guide/SKILL.md").decode()
        readme = zf.read("test-hub/README.md").decode()
        assert not any("test-hub-guide/_hub" in n for n in zf.namelist())
    assert "{{ suite_skills }}" not in guide
    assert "**Analysis Tools**" in guide and "`data-check` (v1.2.0, Official)" in guide
    assert readme.index("## Hub-wide") < readme.index("## Analysis Tools")
    with zipfile.ZipFile(site / "skills" / "test-hub-guide.skill") as zf:
        standalone = zf.read("test-hub-guide/SKILL.md").decode()
    assert standalone == guide
    suite = json.loads((site / "inventory" / "groups.json").read_text())["suite"]
    assert [s["name"] for s in suite["hub_skills"]] == ["test-hub-guide"]
    assert suite["hub_skills"][0]["summary"] == "Where to start"
    index = json.loads((site / ".well-known" / "agent-skills" / "index.json").read_text())
    assert index["skills"][0]["name"] == "test-hub-guide"


def test_install_page_shows_install_everything(tmp_project: Path):
    _enable(tmp_project)
    hub = tmp_project / "hub.yaml"
    hub.write_text(hub.read_text().replace("    - install.html\n", "    - none.html\n"), encoding="utf-8")
    build(tmp_project, base_url=BASE)
    html = (tmp_project / "_site" / "install.html").read_text()
    assert 'id="install-everything"' in html
    assert f"/plugin install test-hub --marketplace {BASE}marketplace.json" in html
    assert f"npx skills add {BASE} --skill '*'" in html
    assert 'href="./bundle/test-hub.zip"' in html


def test_install_page_without_bundle_has_no_section(tmp_project: Path):
    hub = tmp_project / "hub.yaml"
    hub.write_text(hub.read_text().replace("    - install.html\n", "    - none.html\n"), encoding="utf-8")
    build(tmp_project, base_url=BASE)
    html = (tmp_project / "_site" / "install.html").read_text()
    assert "install-everything" not in html
    assert "Customize &rarr; Skills" in html
