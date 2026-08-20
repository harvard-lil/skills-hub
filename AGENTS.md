# Working in this repository

Rules for changing skills-hub. Read [docs/commitments.md](docs/commitments.md)
before changing anything a consumer repository depends on.

## What this repository is

Infrastructure, not content. The skills that ship here (`skills/hub-setup/`)
exist to help people set up hubs and to give the builder something real to build.
Domain skills — legal education, public data, anything else — belong in the
consumer repository that owns that domain.

## Source of truth

- Discovery rules: `packages/skills-hub-builder/src/skills_hub_builder/discover.py`.
  Prose elsewhere describes it; when they disagree, the code is right and the
  prose is a bug.
- The consumer contract: `example/`. It is the executable statement of what a
  consumer must provide. A contract change that does not change `example/` is
  incomplete.
- Site output shape: `packages/skills-hub-builder/src/skills_hub_builder/packager.py`
  (inventory JSON, `.skill` zip layout) and `theme/` (pages and assets).

## Verification

```bash
just test            # 89 tests, no network
just lint
just build-example   # writes example/_site
just build-self      # writes _site
just clean
```

`just test` runs 89 tests. It establishes that the builder and harness behave as
their unit tests specify. It establishes nothing about how a rendered page looks, whether a
deployment succeeded, or whether any skill is any good. Check rendered output by
reading `_site/index.html` and `_site/inventory/*.json`, or by serving the
directory locally.

`skill-eval` runs are not part of `just test`. They call a paid API, need
`OPENROUTER_API_KEY`, and produce non-deterministic scores. Do not run them
speculatively; run them when a skill's instructions changed and someone wants the
evidence.

## Claim boundaries

- `outputs.gpt_actions` and `outputs.claude_extension` write files, and were
  checked against `lawskills-hub` on 2026-08-20. Nobody has confirmed that a
  ChatGPT Custom GPT reads the spec, or that Claude Desktop installs the `.mcpb`.
  Describe them as produced, not as working end to end.
- `templates/mcpb/` is the consumer's, not the builder's. Do not move extension
  assets into this repository; a hub's MCP server, its instructions, and its
  identity belong to the hub that publishes them.
- The builder discovers arbitrarily deep group nesting but only packages and
  inventories groups one level under `skills/`. Deeper skills are counted in the
  build summary and then dropped. Do not document nesting as supported.
- A trace records what a judge model said about one conversation. It is not a
  measurement of skill quality, and a score above the 50-point floor is not a
  release gate.

## Effects and limits

- Do not edit `_site/` or `example/_site/`; both are generated and gitignored.
- Do not edit consumer repositories from here. `lawskills-hub` and
  `pubdata-skills` are separate repositories with their own owners.
- Changing `.github/workflows/build-and-deploy.yml` or `actions/` changes the
  behavior of every consumer pinned to `@main` on their next push. Treat those
  files as published interface.
- Bump the package version in `packages/*/pyproject.toml` when behavior visible
  to a consumer changes. Consumers install from `@main`, so there is no release
  to hide behind.

## Documentation

Route reasoning to its home rather than restating it here: adopted invariants and
known gaps in [docs/commitments.md](docs/commitments.md), decisions and their
alternatives in [docs/adr/](docs/adr/), sequencing in
[docs/roadmap.md](docs/roadmap.md), dated evidence in [docs/research/](docs/research/).
