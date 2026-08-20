# Roadmap

What is being pursued next, and what is unresolved. Nothing here is a commitment;
adopted invariants are in [commitments.md](commitments.md).

There is no issue tracker attached to this repository yet, so this file is the
task home. Move items out as soon as there is a better one.

## Now: prove the extraction

**Adapt `lawskills-hub` to consume this repository with no visible change to its
published site.** The four gaps found by reading both trees — group metadata,
meta skill bodies, `actions/`, `packages/mcpb/` — are closed, and a build of that
hub now matches a build made with its own scripts everywhere except group
ordering and the `design.pitch` duplication. The remaining work is confirmation
this repository cannot do for itself: the site has not been deployed from the
shared workflow, and neither ChatGPT nor Claude Desktop has been pointed at the
generated packages. Evidence and the residual diffs are in
[research/2026-08-20-lawskills-hub-parity.md](research/2026-08-20-lawskills-hub-parity.md).

**Take `pubdata-skills` from zero to a deployed site.** Created 2026-08-19 for the
Public Data Project and the first consumer built on this infrastructure rather
than migrated onto it. It exercises the opposite direction from `lawskills-hub`:
whether the contract in `example/` is enough to start from nothing. `example/`
carries the same "Data Monitoring Toolkit" framing, so keep the two from drifting
into two different answers to the same question.

## Next: settle the vocabulary the packaging outputs use

`outputs.gpt_actions` and `outputs.claude_extension` now write files, ported from
`lawskills-hub`'s `scripts/build_actions.py` and `scripts/build_mcpb.py`. The
Actions API kept that hub's `persona` vocabulary in its paths and JSON keys,
because published Custom GPTs and `.mcpb` extensions already call those
addresses, while the rest of the builder says `group`. Two names for one thing is
a cost that grows with each consumer. Either rename the API and accept a breaking
change for whoever has already configured a GPT, or state that `persona` is the
wire name and stop apologizing for it.

`headline` and `pitch` are the same problem one level down: `GroupInfo` has
neither, so `actions/personas/*.json` derives `headline` from the group
description and reads `pitch` out of the `design` block it also publishes whole.

## Defects worth fixing before more consumers arrive

Each is described with its evidence in [commitments.md](commitments.md).

- Groups nested more than one level under `skills/` are discovered, counted in
  the build summary, and then dropped from packaging and inventory. Decide
  whether nesting is supported or not, and make the code and the `hub-setup-meta`
  skill agree.
- `actions/eval/action.yml` passes a secret's name where its value is needed.
  Either fix it or delete it in favour of `.github/workflows/eval.yml`, which
  takes the key correctly.
- `parse_frontmatter` is line-based. A block-scalar description silently becomes
  `">"`. Parsing the frontmatter as YAML would remove a whole class of quiet
  breakage, at the cost of rejecting files that currently limp through.
- `skills/hub-setup/hub-setup-meta/SKILL.md` sends users to a `CONTRIBUTING.md`
  that does not exist here. Either write one for infrastructure contributors or
  change the pointer.

## Open questions

- Is there a preview step? There is no recipe for serving a built `_site`, and
  nothing in the repository establishes how a contributor checks a rendered page.
  `lawskills-hub`'s guide uses `python -m http.server -d _site`.
- Should the builder validate anything? Today a malformed `SKILL.md` publishes as
  a malformed listing. A `skills-hub-builder check` that a consumer's CI could run
  before deploying would catch the frontmatter and nesting failures above at the
  point where someone can act on them. Not proposed, just noticed.
- When consumers pin. Every consumer tracks `@main` today; see
  [adr/2026-08-20-distribute-from-main.md](adr/2026-08-20-distribute-from-main.md).
  The cost of that becomes real at the point where a change here breaks a
  consumer's deploy, which has not happened yet.
- Who owns skill-authoring guidance. The authoring philosophy lives in
  `lawskills-hub`'s `CONTRIBUTING.md`, and the same ideas are re-encoded in
  `skills/hub-setup/writing-a-skill/SKILL.md` here. Two copies drift. Whether the
  hub-setup skills should become the canonical statement is unresolved.
