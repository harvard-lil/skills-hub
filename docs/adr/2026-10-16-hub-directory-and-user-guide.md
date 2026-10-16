# Separate what the agent reads, what the person reads, and what only the hub reads

- Status: Accepted
- Recorded: 2026-10-16

## Context

A skill directory held one kind of file until now: whatever was in it went into
the `.skill` zip. That put three audiences in one place without saying which
file was for whom.

- **The agent** reads `SKILL.md` and anything it points to. Its frontmatter
  `description` is a routing signal, written for an agent deciding whether the
  skill applies ("Use when someone names a dataset…").
- **The person installing the skill** had nothing of their own. Site cards
  showed the agent-facing `description`, and there was nowhere to put
  instructions on how to use a skill well, of the kind user testing produces.
- **The hub** needs files that should not ship. `rubric.yaml` was packaged into
  every standalone and meta zip, so evaluation criteria and scripted test
  scenarios reached everyone who installed the skill, and any agent that
  listed the skill's directory.

## Decision

Each file in a skill directory has one audience, and the audience decides
whether it ships:

| Path | Audience | Packaged |
|---|---|---|
| `SKILL.md`, `references/`, other files | agent | yes |
| `README.md` | person using the skill | yes |
| `_hub/metadata.yaml` | hub | no |
| `_hub/rubric.yaml` | hub (evaluation) | no |

- `_hub/` at the root of a skill directory is never packaged, in a standalone
  zip or bundled into a meta zip. A `_hub/` further down is ordinary content.
- `_hub/metadata.yaml` holds `summary`: one sentence for a person deciding
  whether to install the skill. Cards and the skill page show it, and fall back
  to `description` without it. The inventory carries both fields, since agents
  reading the inventory still choose by `description`.
- `README.md` is the guide for the person. The skill page leads with it and
  shows the `SKILL.md` body beneath it as the instructions the agent reads. It
  also ships, so the agent can answer "how do I use this?" if the `SKILL.md`
  tells it to read the file.
- `skill-eval` reads a rubric only from `<skill>/_hub/rubric.yaml`, for each
  skill the builder would discover. Outside `_hub/`, `rubric.yaml` is an
  ordinary filename: a skill may ship one as content, and neither the builder
  nor the harness treats it as a rubric.
- Amended 2026-10-16: the first version also read a `rubric.yaml` beside the
  `SKILL.md`, with a build warning, while `pubdata-skills` and `lawskills-hub`
  moved theirs. Both have moved, and that path was removed. The first version
  also raised on a `rubric.yaml` with no `SKILL.md` to pair with; finding
  rubrics from skills rather than skills from rubrics makes that case
  impossible.

## Alternatives considered

**Hub fields in `SKILL.md` frontmatter**, under the Agent Skills spec's
`metadata` map. One file per skill, but the frontmatter travels with the skill
into the agent's context, and the builder's frontmatter parser is line-based and
cannot read nested maps (see [commitments.md](../commitments.md)).

**Separate hub files beside `SKILL.md`** (`skill.yaml`, `rubric.yaml`) with a
deny-list in `hub.yaml`. Works, but every new hub-only file needs a list entry,
and a missed entry ships silently. A directory makes the rule one line and gives
later hub-only material — screenshots for the guide, eval fixtures — an obvious
home.

**`.hub/` instead of `_hub/`.** Dot-directories are hidden by default in file
browsers and skipped by some tools, which makes the convention harder to
discover. Discovery already ignored `_`-prefixed directories, so `_hub/` needed
no change there.

**Keep `README.md` out of the package.** Anthropic's skill-authoring guidance
discourages auxiliary files such as a README inside a skill. That advice is
about clutter aimed at the agent. A guide for the person costs nothing at
runtime, since an agent reads only `SKILL.md` and the files it is pointed to,
and it is useful to anyone who opens the installed folder.

## Consequences

- A rubric saved anywhere but `_hub/rubric.yaml` is not evaluated, and if it is
  inside the skill directory it is packaged. Nothing warns about it.
- `inventory/<group>.json` gains `summary` (a string or `null`) and `has_guide`
  per skill and meta skill. Both are additions; no field changed meaning.
- The builder still does not check what a summary or guide says, and no field
  sets a group's user-facing blurb; `lawskills-hub` still uses `design.pitch`.
  A `summary` in `group.yaml` would be the matching change at group level.
- This supersedes the consequence in
  [the meta-skill record](2026-08-20-meta-skill-bundling.md) that `rubric.yaml`
  ships in both standalone and bundled packages.
