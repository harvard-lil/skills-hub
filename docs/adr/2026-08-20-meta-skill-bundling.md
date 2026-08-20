# Bundle group skills into a meta skill package

- Status: Accepted
- Recorded: 2026-08-20, from the code as it stands

## Context

A group is a set of related skills. Installing them one at a time is tedious, and
an agent holding several skills from one domain still needs to decide which
applies to the request in front of it.

Agents practice progressive disclosure: they read names and descriptions, then
load a full skill body only when it looks relevant. Any bundle has to preserve
that, or installing a group means paying for every skill's body on every turn.

## Decision

Treat a skill whose `name` ends in `-meta` as its group's router. At build time
`packager.py`:

- replaces `{{ bundled_skills }}` in the meta skill's body with a generated list
  of the group's other skills — name, version, status, description, and the path
  to the full instructions;
- writes each sibling into the meta skill's zip under
  `references/<skill-name>/subskill.md`, carrying that skill's own `references/`
  and `rubric.yaml` along beneath it;
- also publishes each sibling as an ordinary standalone `.skill`.

The installed meta skill is therefore one skill whose body is a routing table,
with the bodies it routes to sitting on disk next to it, read only when the
router decides to read one.

## Alternatives considered

**Install skills individually.** Already supported and still published; the
bundle is an addition, not a replacement. Alone it leaves the user to find and
install each skill and gives the agent no routing guidance.

**Concatenate the group's skills into one large `SKILL.md`.** Simplest to build,
and it defeats progressive disclosure: every request pays for every skill.

**A manifest of install URLs the agent fetches at runtime.** Keeps the package
small but makes the skill useless offline and puts a network call between the
user and an answer.

## Consequences

- `-meta` is a reserved suffix in every consumer. `lawskills-hub`'s contributor
  guide already tells authors not to use it.
- The routing quality is the meta skill author's problem, not the builder's. The
  builder guarantees the list is complete and the paths resolve; whether the
  router chooses well is what a rubric is for.
- Zips carry whatever is in the skill directory, so a `rubric.yaml` ships to
  users in both the standalone package and the bundle. It is inert at runtime
  and it is extra bytes in every download.
- The meta skill's `SKILL.md` in the zip is generated, not the file on disk, so
  a build must run before the placeholder means anything. Reading the source
  file shows `{{ bundled_skills }}`.
