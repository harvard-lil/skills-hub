# Skills Hub

Shared infrastructure for publishing and evaluating collections of AI agent skills.
A consumer repository holds the skills; this repository holds the generator, the
evaluation harness, and the GitHub Actions that tie them together, so that several
hubs can be built the same way without each one carrying its own build scripts.

Status: early. `skills-hub-builder` is at `0.2.0` and `skill-eval` at `0.1.0`, with
no tagged release and no PyPI publication. Consumers install from git.

## Packages

### `skills-hub-builder`

A static site generator for a directory of agent skills. Given a project with
`hub.yaml` and `skills/`, `skills-hub-builder build` writes to `_site/`:

- `index.html`, `css/`, `js/` — a one-page site that loads the inventory JSON in
  the browser and renders group and skill cards with filtering
- `install.html` — a generic "Get Started" page: how to install a `.skill` pack
  in an agent, with one-click cards appearing only when `--custom-gpt-url` or a
  built `.mcpb` supplies them. A project `website/install.html` replaces it;
  `theme.exclude` can drop it
- `skills/<group>/<name>.skill` — a zip per skill, and per meta skill
- `inventory/groups.json` and `inventory/<group>.json` — the data the page reads,
  and the same data an agent can read directly
- `traces/` — copied from the project's `traces/` directory if present, except
  `index.html`, which is left to whatever `website/traces/index.html` rendered.
  The bundled theme has no page that displays them.

Two further outputs are off by default and switched on in `hub.yaml`:

- `outputs.gpt_actions` writes `actions/` — `openapi.json`, `openapi.yaml`, and
  a JSON file per group, per skill, and per skill reference. A ChatGPT Custom GPT
  points an Action at the spec and fetches the rest as plain GETs. The wire
  vocabulary is `persona`, not `group`.
- `outputs.claude_extension` writes `packages/mcpb/<name>.mcpb`, zipped from the
  project's own `templates/mcpb/` with `{{base_url}}`, `{{personas_json}}` and
  `{{personas_summary}}` substituted. The builder ships no extension assets of
  its own; `<name>` is the `name` in the project's `manifest.json`.

Run with `uvx`:

```bash
uvx --from git+https://github.com/harvard-lil/skills-hub#subdirectory=packages/skills-hub-builder \
    skills-hub-builder build
```

The `--custom-gpt-url` option and the matching `custom-gpt-url` workflow input
reach templates as `custom_gpt_url`; `mcpb_download_url` is supplied alongside it.

### `skill-eval`

An LLM-as-judge harness. It discovers `rubric.yaml` files under `skills/`, replays
each rubric's scripted user turns against a model with the `SKILL.md` as system
prompt, scores the transcript with a judge model, and writes a JSON trace per run
to `traces/`. Each scenario also runs against a bare model with no skill installed,
recorded under version `_null`, so a hub can see whether the skill beats the
baseline.

Run with `uvx`:

```bash
uvx --from git+https://github.com/harvard-lil/skills-hub#subdirectory=packages/skill-eval \
    skill-eval run
```

Running evaluations calls a paid API. The default configuration points at
OpenRouter and reads `OPENROUTER_API_KEY`; without a key the tests skip.

## Project layout

```
skills-hub/
├── packages/
│   ├── skills-hub-builder/     # Site generator + packager
│   └── skill-eval/             # Evaluation harness
├── actions/                    # Composite actions (build, eval)
├── .github/workflows/          # Reusable workflows consumers call
├── skills/                     # This repo's own hub-setup skills
├── hub.yaml                    # This repo builds itself as a hub
├── example/                    # Minimal example consumer project
└── docs/                       # Commitments, decisions, roadmap, research
```

This repository is also a consumer of its own builder: `hub.yaml` and
`skills/hub-setup/` produce one group holding three skills and a meta skill, so a
change that breaks the consumer contract breaks this repo's own build.

## Using it in your project

[example/](example/) is a working consumer project — the fastest way to see the
whole contract at once. In full, a consumer needs:

| Path | Required for | Purpose |
|---|---|---|
| `hub.yaml` | site | Title, org, theme, output toggles |
| `skills/<group>/group.yaml` | group labels | Without it the group still builds, with a title-cased id and no description. An optional integer `order` sorts the group ahead of unordered (alphabetical) ones |
| `skills/<group>/<skill>/SKILL.md` | everything | YAML frontmatter plus the instructions |
| `skills/<group>/<skill>/rubric.yaml` | evaluation | Criteria, anti-patterns, scenarios |
| `templates/meta-skill.md` | meta skill bodies | A wrapper every meta skill is composed into. Without it, a meta `SKILL.md` keeps its own body and its `{{ bundled_skills }}` placeholder is expanded in place |
| `templates/mcpb/` | `outputs.claude_extension` | The extension's own files, `manifest.json` at the root |
| `eval.yaml` | evaluation | Models under test, judge models, API base URL |
| `tests/test_skills.py` | evaluation | One line: `from skill_eval.test_skills import *` |
| `.github/workflows/deploy.yml` | deployment | One job calling `harvard-lil/skills-hub/.github/workflows/build-and-deploy.yml@main` |

Deployment also requires GitHub Pages to be enabled on the consumer repository
with Source set to GitHub Actions; the workflow cannot turn that on itself.

The discovery rules — what counts as a group, what counts as a skill, how meta
skills bundle their siblings — are defined in
[`packages/skills-hub-builder/src/skills_hub_builder/discover.py`](packages/skills-hub-builder/src/skills_hub_builder/discover.py)
and summarized in [docs/commitments.md](docs/commitments.md).

## Development

`just --list` is authoritative. The recipes routine work uses:

| Recipe | What it does |
|---|---|
| `just dev` | `uv sync --all-packages` |
| `just test` | Run both package test suites |
| `just lint` / `just fmt` | Ruff check / format over `packages/` |
| `just inspect-example` | Print the discovered skill tree for `example/` |
| `just build-example` | Build `example/` into `example/_site` |
| `just build-self` | Build this repo's own hub into `_site` |
| `just discover-example` | List the example's rubrics and scenarios |
| `just clean` | Remove `_site` and `example/_site` |

`just test` runs 89 tests as of 2026-08-20 and exercises the builder's
configuration, discovery, packaging, rendering, GPT Actions and extension
packaging plus the harness's runner, evaluator, and trace writer. It makes no
network calls and does not evaluate any skill's quality.

## Documentation

- [AGENTS.md](AGENTS.md) — rules for changing this repository
- [docs/commitments.md](docs/commitments.md) — the consumer contract, checked
  facts, known gaps, and what is deliberately out of scope
- [docs/adr/](docs/adr/) — why the structure is what it is
- [docs/roadmap.md](docs/roadmap.md) — what is next and what is unresolved
- [docs/research/](docs/research/) — checked evidence, with dates
