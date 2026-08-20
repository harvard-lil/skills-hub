# Discover skills by filesystem convention

- Status: Accepted
- Recorded: 2026-08-20, from the code as it stands

## Context

The builder has to know which directories are skills, which are groups, and how
they relate. The people adding skills are often not engineers, and the stated
goal in `skills/hub-setup/group.yaml` is to "favor convention over configuration."

## Decision

Walk `skills/` and infer the tree from what is on disk, in
`skills_hub_builder/discover.py`:

- a directory containing `group.yaml` is a group;
- a directory containing `SKILL.md` is a skill;
- a directory can be both, which is how a group carries its own meta skill;
- a directory with neither is still traversed if a descendant has one;
- directories beginning with `.` or `_` are skipped.

Group metadata is optional. Without `group.yaml`, a directory that contains
skills is still a group, labelled from its title-cased id with no description.

Adding a skill is therefore adding a directory. Nothing central lists it.

## Alternatives considered

**A manifest file enumerating skills and groups.** Explicit and diffable, and it
would make ordering and inclusion decisions obvious. It also adds a second place
to edit for every addition, and a class of failure — the file exists but is not
listed — that convention cannot produce.

**Frontmatter-declared grouping.** Each `SKILL.md` naming its own group, with
directory layout free. Decouples grouping from location, at the cost of making
the tree unreadable without parsing every file.

## Consequences

- Discovery has no error state for a misplaced directory. A skill in the wrong
  place is published in the wrong place rather than reported.
- `parse_frontmatter` splits each line on the first colon instead of parsing
  YAML. Single-line values work; a block scalar such as `description: >` yields
  `">"` as the description. Recorded in
  [../commitments.md](../commitments.md).
- Recursion is unbounded but packaging is not: only groups one level under
  `skills/` are packaged and inventoried, so a deeper skill is counted in the
  build summary and then dropped. Either the recursion or the packaging is wrong;
  which one is a question for whoever needs nesting first.
