# Publish one bundle of every skill in a hub

- Status: Proposed
- Recorded: 2026-10-28, with a prototype checked against `pubdata-skills`

## Context

A hub publishes a `.skill` per skill and a meta pack per group. Someone who
wants the whole hub installs one pack per group: four uploads for
`pubdata-skills`, five for `lawskills-hub`. The meta pack exists because a
skill upload registers one skill, so a group's other skills have to ride inside
it as references with a router in front
([meta-skill bundling](2026-08-20-meta-skill-bundling.md)).

Several clients now install many skills in one step, each registered with its
own name and description (sources checked 2026-10-28):

- claude.ai and the Claude desktop app take a plugin zip through
  Customize > Plugins > Upload plugin, up to 200 MB and 5,000 files, and sync it
  to Cowork and Claude Code
  ([plugins](https://claude.com/docs/plugins/overview.md),
  [platform support](https://claude.com/docs/plugins/platform-support.md)).
- Claude Code installs a plugin from a marketplace added by the URL of a
  `marketplace.json`, with an `archive` plugin source: a zip over HTTPS pinned
  by sha256, root at the top of the zip or one directory down, Claude Code
  2.1.224 or later. No git access to the source repository is needed
  ([host a marketplace](https://code.claude.com/docs/en/plugins/host-marketplace.md),
  [marketplace reference](https://code.claude.com/docs/en/plugins/marketplace-reference.md)).
- The `skills` CLI (`npx skills add`, vercel-labs/skills 1.7.4) installs from a
  site URL by reading `.well-known/agent-skills/index.json`, a format proposed
  for the Agent Skills specification in
  [agentskills#254](https://github.com/agentskills/agentskills/pull/254) and not
  yet adopted there. It records the source in `skills-lock.json` and updates from
  it.

All three read from the published site, which matters for a hub whose
repository is private while its Pages site is public.

## Decision

Under `outputs.suite_bundle` (off by default), the builder writes:

- `bundle/<name>.zip`: `<name>/.claude-plugin/plugin.json`,
  `<name>/skills/<skill>/` for every non-meta skill, and a generated `README.md`
  that lists the skills and says which are official and which are drafts.
- `marketplace.json`: one plugin entry with an `archive` source and the zip's
  sha256.
- `.well-known/agent-skills/index.json` and one `<skill>.zip` per skill with
  `SKILL.md` at its root, which the `skills` CLI requires.
- An "Install everything" section on the bundled `install.html`, and a `suite`
  block in `inventory/groups.json` (an added key; existing keys are unchanged).

Zips are written with fixed timestamps and sorted entries, so an unchanged tree
gives identical bytes, pins, and version. The plugin version is `suite.version`
from `hub.yaml` when set, otherwise `0.0.0+<content hash>`.

Meta skills stay out of the bundle. Where every skill is registered on its own,
the client's own skill selection does the routing, and a router would add a
second description competing for the same requests.

A skill directly under `skills/`, in no group, is a hub-level skill. It leads
the bundle and the index, is written standalone as `skills/<name>.skill`, and
its `{{ suite_skills }}` placeholder becomes a listing of the other skills by
group and name. This is where a hub puts an orientation skill that applies
across groups. The listing names skills instead of giving paths so the same
text works in the bundle and standalone.

## Alternatives considered

**A hub-wide meta pack**: one `-meta` skill bundling every skill under
`references/`, as group packs do. It would give skill-upload-only clients one
upload for everything. It also puts every request through one router and
duplicates every skill body already published. The plugin upload covers claude.ai
and the desktop app, so this is held back until a client needs it.

**A marketplace in the consumer repository** (`.claude-plugin/marketplace.json`
at the repository root, plugin source `./`). Claude Code and the claude.ai
Add marketplace dialog read it from git, so it works only for people who can
clone the repository, and it would install meta skills' unexpanded
`{{ bundled_skills }}` sources unless every entry listed skill paths by hand.

**Only the bundle zip, no well-known index.** `npx skills add <zip url>` also
installs all skills from the bundle, but records no source, so `npx skills
update` cannot find new versions.

## Consequences

- The site carries a second copy of every skill (the per-skill index zips) and
  a third inside the bundle. For `pubdata-skills` that is under 200 KB.
- `.well-known/` is a dotfile directory. `actions/upload-pages-artifact` v3
  includes it; v4 drops dotfiles, and v5 adds `include-hidden-files`. A
  Dependabot bump of that action has to keep it.
- Two skills with one `name` in different groups now fail the build when the
  bundle is on, because they would collide in a flat `skills/` directory.
- A plugin namespaces its skills (`<name>:<skill>`) in Claude. A person who
  installs the bundle and a group pack gets two entries for the same work.
  The install page says to choose one.
- Nothing here has been installed from a published site. What was checked, and
  how, is in the claim boundaries in [AGENTS.md](../../AGENTS.md).
