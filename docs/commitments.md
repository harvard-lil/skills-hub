# Commitments and known facts

What must stay true, what has been checked, and what is deliberately absent.
Decisions and their alternatives live in [adr/](adr/); sequencing lives in
[roadmap.md](roadmap.md).

## Adopted invariants

**A consumer repository holds content, not build machinery.** Everything a hub
needs to become a website — discovery, packaging, templating, deployment — lives
here. If a consumer has to write a build script, that is a gap in this repository.

**The contract is a filesystem convention, not a manifest.** A directory with a
`group.yaml` is a group; a directory with a `SKILL.md` is a skill; a directory can
be both. Nothing enumerates skills in a central file, so adding a skill is adding
a directory. See [adr/2026-08-20-filesystem-convention-discovery.md](adr/2026-08-20-filesystem-convention-discovery.md).

**A meta skill is identified by its name.** A skill whose `name` ends in `-meta`
is a router for its group. Its `.skill` zip bundles the group's other skills under
`references/<skill-name>/subskill.md`, and its `{{ bundled_skills }}` placeholder
is replaced at build time with the generated listing. Consumers must not use the
`-meta` suffix for an ordinary skill. See
[adr/2026-08-20-meta-skill-bundling.md](adr/2026-08-20-meta-skill-bundling.md).

**Build templates are the consumer's.** `templates/meta-skill.md` and
`templates/mcpb/` are read from the consumer project, never shipped by the
builder. A project with neither keeps the placeholder-in-the-skill behavior and
produces no extension, so adding these files is opt-in and removing them is a
clean revert.

**Deployment is one job in one workflow file.** A consumer's entire CI is a call
to `harvard-lil/skills-hub/.github/workflows/build-and-deploy.yml@main`. Adding a
required step to a consumer's workflow breaks this.

**Output is static files.** The builder writes a directory that any static host
can serve. Nothing in the published artifact requires a server, a database, or a
running process.

**The inventory JSON is a public interface.** `inventory/groups.json` and
`inventory/<group>.json` are read by the site's own JavaScript and, by design, by
agents fetching the hub directly. Changing their shape is a breaking change for
both readers.

**Evaluation records evidence; it does not gate.** Traces are written per run,
accumulate under `traces/<group>/<skill>/<version>/`, and are committed to the
consumer's repository. Each scenario also runs with no skill installed, under
version `_null`, so the skill can be compared against a bare model. See
[adr/2026-08-20-llm-judge-with-null-baseline.md](adr/2026-08-20-llm-judge-with-null-baseline.md).

## Checked facts

Checked 2026-08-20 against the working tree.

- `just test` passes: 89 tests, 0.6s, no network access.
- `just build-example` produces 2 skill zips plus 1 meta zip across 2 groups,
  `index.html`, `inventory/groups.json`, and 2 per-group inventory files.
- `just build-self` produces 3 skill zips plus 1 meta zip in one group.
- The meta zip's layout was inspected: `risk-assessment-meta/SKILL.md`,
  `risk-assessment-meta/references/analyzing-data-risk/subskill.md`, and the
  child skill's own `references/` and `rubric.yaml` carried along beneath it.
  `{{ bundled_skills }}` was expanded to a name, version, status, description,
  and the `references/.../subskill.md` path.
- The site renders one page. Group and skill cards are built in the browser by
  `js/app.js` from the inventory JSON; the HTML ships a "Loading skills
  inventory…" placeholder.
- This repository has no `.git` directory and no remote. Every file is dated
  2026-08-19 or later, and there is no commit history to consult for rationale.
- The builder has now been pointed at `lawskills-hub`, whose site was previously
  built by its own scripts. Against a build of that site made with the old
  scripts, this builder reproduces both pages, both CSS files, `traces/index.html`,
  all 14 non-meta `.skill` zips and 17 of the 25 files under `actions/` byte for
  byte; the five meta `.skill` zips match on member bytes, differing only in a zip
  entry timestamp that varied between two runs of the old scripts too. Of the 16
  files that genuinely differ, 8 under `actions/` plus the `.mcpb` differ by group
  ordering and `design.pitch` alone, and the other 7 are the inventory and
  JavaScript changes the adaptation intended. See
  [research/2026-08-20-lawskills-hub-parity.md](research/2026-08-20-lawskills-hub-parity.md).

## Known gaps

Each was checked on 2026-08-20 and none is fixed.

*(Closed 2026-08-20: group ordering. `group.yaml` now takes an optional integer
`order`; ordered groups sort ascending ahead of unordered ones, which stay
alphabetical. Both `lawskills-hub` (matching its old `personas.yaml` order) and
`pubdata-skills` (pipeline order) set it. `lawskills-hub`'s `js/app.js` still
carries a now-redundant display-order pin.)*

**Group nesting deeper than one level is silently dropped.** `discover_tree`
recurses without limit, but `_package_skills` and `build_inventory` iterate only
`tree.children`. Built with a fixture holding `skills/outer/inner/deep-skill/`,
the summary reported "Built 1 skills across 1 groups" while `inventory/outer.json`
listed `"skills": []` and no `.skill` file was written. The `hub-setup-meta` skill
tells users "Groups can nest arbitrarily," which is not true of the output.

**Frontmatter is parsed line by line, not as YAML.** `parse_frontmatter` splits
each line on the first colon. A block scalar `description: >` yields the
description `">"`, and the body lines are discarded. Nested `metadata: / version:`
happens to work because indentation is stripped. All 19 `SKILL.md` files in
`lawskills-hub` use single-line descriptions today, so this is latent there — but
that repository's `CONTRIBUTING.md` shows `description: >` in its example
frontmatter, so a contributor following the guide would produce a broken listing.

**`GroupInfo` has no `headline` or `pitch`.** `lawskills-hub`'s old
`personas.yaml` had both as top-level fields; a `group.yaml` has `description`
and whatever the author puts under `design`. The published `actions/personas/*.json`
therefore carries `pitch` twice — once at the top level, once inside `design` —
because the builder passes the `design` block through untouched. Harmless, and a
sign that these two field sets have not been reconciled.

**`actions/eval/action.yml` appears unable to authenticate.** It sets
`OPENROUTER_API_KEY: ${{ inputs.api-key-secret }}`, where that input defaults to
the string `"OPENROUTER_API_KEY"` — the name of a secret, not its value, and a
composite action cannot read the `secrets` context. Read from the file; not
confirmed by running the action. `.github/workflows/eval.yml` takes the key as a
real secret and does not have this problem.

**`hub-setup-meta` points at a `CONTRIBUTING.md` that does not exist here.**

## Facts not established

- The reusable workflows and composite actions have never been observed running.
  `build-and-deploy.yml` and `eval.yml` are checked here only by reading them;
  the local tree carries no git history or remote from which a run could be
  confirmed.
- No evaluation has been run through `skill-eval` here. There is no `traces/`
  directory, so the judge prompts are supported only by unit tests with stubbed
  clients. The index rebuild has been exercised on real data once: on 2026-08-20
  `rebuild_index` was run over `lawskills-hub`'s 160 committed traces and
  reproduced its `index.json` byte for byte.
- No Custom GPT has been pointed at a generated `actions/` tree, and no Claude
  Desktop has installed a generated `.mcpb`. Both outputs are checked against a
  previous generator's output, not against the clients that consume them.
- Nothing measures whether a hub site is usable by the agents it is meant for.

## Out of scope

**Hosting anything dynamic.** Output is static files on GitHub Pages. A hub that
needs a search backend, an authenticated area, or a request-time API is a
different product.

**Judging skill content.** The builder packages whatever `SKILL.md` says. It does
not lint prose, enforce a description format, or check that boundaries are
stated. Authoring standards belong to the consumer — `lawskills-hub`'s
`CONTRIBUTING.md` is the worked example — and to the `hub-setup` skills here.

**Owning domain skills.** Legal education skills belong to `lawskills-hub`;
public data skills belong to `pubdata-skills`.

**Being a general skills registry.** This publishes hubs that someone curates. It
does not aggregate, index, or rank skills across hubs.
