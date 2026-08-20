"""Tests for skill tree discovery."""

from pathlib import Path

import pytest

from skills_hub_builder.discover import (
    GroupInfo,
    SkillInfo,
    SkillNode,
    discover_tree,
    parse_frontmatter,
)


class TestParseFrontmatter:
    def test_basic(self, tmp_path: Path):
        p = tmp_path / "SKILL.md"
        p.write_text(
            "---\nname: my-skill\ndescription: Does things\nversion: 1.0.0\n---\n\n# Body\n",
            encoding="utf-8",
        )
        fm = parse_frontmatter(p)
        assert fm["name"] == "my-skill"
        assert fm["description"] == "Does things"
        assert fm["version"] == "1.0.0"

    def test_missing_frontmatter(self, tmp_path: Path):
        p = tmp_path / "SKILL.md"
        p.write_text("# No frontmatter here\n", encoding="utf-8")
        with pytest.raises(ValueError, match="No YAML frontmatter"):
            parse_frontmatter(p)

    def test_multiline_description_takes_first_line(self, tmp_path: Path):
        p = tmp_path / "SKILL.md"
        p.write_text(
            "---\nname: x\ndescription: Short desc\nstatus: official\n---\n",
            encoding="utf-8",
        )
        fm = parse_frontmatter(p)
        assert fm["description"] == "Short desc"
        assert fm["status"] == "official"


class TestDiscoverTree:
    def test_discovers_groups_and_skills(self, tmp_project: Path):
        tree = discover_tree(tmp_project / "skills")

        assert tree.id == "skills"
        assert len(tree.children) == 2  # analysis, monitoring

        # Find analysis group
        analysis = next(c for c in tree.children if c.id == "analysis")
        assert analysis.is_group
        assert analysis.group.label == "Analysis Tools"
        assert analysis.group.description == "Tools for analyzing things"

    def test_meta_skill_detected(self, tmp_project: Path):
        tree = discover_tree(tmp_project / "skills")
        analysis = next(c for c in tree.children if c.id == "analysis")

        meta = analysis.meta_skill()
        assert meta is not None
        assert meta.name == "analysis-meta"
        assert meta.is_meta

    def test_child_skills_excludes_meta(self, tmp_project: Path):
        tree = discover_tree(tmp_project / "skills")
        analysis = next(c for c in tree.children if c.id == "analysis")

        children = analysis.child_skills()
        assert len(children) == 1
        assert children[0].name == "data-check"
        assert children[0].version == "1.2.0"
        assert children[0].status == "official"

    def test_group_without_group_yaml(self, tmp_project: Path):
        tree = discover_tree(tmp_project / "skills")
        monitoring = next(c for c in tree.children if c.id == "monitoring")

        # Still a group (has children), just no explicit metadata
        assert monitoring.is_group
        assert monitoring.group is None
        assert monitoring.label == "Monitoring"  # derived from id

    def test_all_skills_flat(self, tmp_project: Path):
        tree = discover_tree(tmp_project / "skills")
        all_skills = tree.all_skills()

        names = [s.name for s in all_skills]
        assert "data-check" in names
        assert "watch-feeds" in names
        assert "analysis-meta" not in names  # meta excluded

    def test_skips_hidden_directories(self, tmp_project: Path):
        hidden = tmp_project / "skills" / ".hidden"
        hidden.mkdir()
        (hidden / "SKILL.md").write_text(
            "---\nname: secret\ndescription: hidden\n---\n", encoding="utf-8"
        )

        tree = discover_tree(tmp_project / "skills")
        all_names = [s.name for s in tree.all_skills()]
        assert "secret" not in all_names

    def test_skips_underscore_directories(self, tmp_project: Path):
        under = tmp_project / "skills" / "_drafts"
        under.mkdir()
        (under / "SKILL.md").write_text(
            "---\nname: draft\ndescription: wip\n---\n", encoding="utf-8"
        )

        tree = discover_tree(tmp_project / "skills")
        all_names = [s.name for s in tree.all_skills()]
        assert "draft" not in all_names

    def test_deeply_nested_groups(self, tmp_path: Path):
        """Arbitrary nesting works."""
        skills = tmp_path / "skills"
        deep = skills / "level1" / "level2" / "level3"
        deep.mkdir(parents=True)
        (deep / "SKILL.md").write_text(
            "---\nname: deep-skill\ndescription: nested\n---\n",
            encoding="utf-8",
        )

        tree = discover_tree(skills)
        all_skills = tree.all_skills()
        assert len(all_skills) == 1
        assert all_skills[0].name == "deep-skill"


class TestSkillNode:
    def test_is_group_with_children(self):
        node = SkillNode(id="x", path=Path("."))
        child = SkillNode(id="y", path=Path("."), skill=SkillInfo(name="y", description=""))
        node.children.append(child)
        assert node.is_group is True

    def test_is_group_with_group_info(self):
        node = SkillNode(id="x", path=Path("."), group=GroupInfo(label="X"))
        assert node.is_group is True

    def test_not_group_when_empty(self):
        node = SkillNode(id="x", path=Path("."))
        assert node.is_group is False

    def test_label_from_group(self):
        node = SkillNode(id="x", path=Path("."), group=GroupInfo(label="Custom Label"))
        assert node.label == "Custom Label"

    def test_label_derived_from_id(self):
        node = SkillNode(id="my-cool-group", path=Path("."))
        assert node.label == "My Cool Group"


class TestGroupOrdering:
    def _make_group(self, skills: Path, name: str, order: int | None):
        grp = skills / name
        grp.mkdir()
        lines = [f"label: {name.title()}\n"]
        if order is not None:
            lines.append(f"order: {order}\n")
        (grp / "group.yaml").write_text("".join(lines), encoding="utf-8")

    def test_explicit_order_beats_alphabetical(self, tmp_path: Path):
        skills = tmp_path / "skills"
        skills.mkdir()
        self._make_group(skills, "alpha", order=3)
        self._make_group(skills, "beta", order=1)
        self._make_group(skills, "gamma", order=2)

        tree = discover_tree(skills)
        assert [c.id for c in tree.children] == ["beta", "gamma", "alpha"]

    def test_unordered_groups_sort_alphabetically_after_ordered(self, tmp_path: Path):
        skills = tmp_path / "skills"
        skills.mkdir()
        self._make_group(skills, "zebra", order=1)
        self._make_group(skills, "apple", order=None)
        self._make_group(skills, "mango", order=None)

        tree = discover_tree(skills)
        assert [c.id for c in tree.children] == ["zebra", "apple", "mango"]

    def test_no_orders_keeps_alphabetical(self, tmp_project: Path):
        tree = discover_tree(tmp_project / "skills")
        assert [c.id for c in tree.children] == sorted(c.id for c in tree.children)
