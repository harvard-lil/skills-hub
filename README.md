# Skills Hub

Build tooling for publishing a collection of AI agent skills as a static website,
and for evaluating those skills. A hub repository holds only skills and a little
configuration. This repository holds the site generator, the evaluation harness,
and the GitHub workflows that run them.
[lawskills-hub](https://github.com/harvard-lil/lawskills-hub) is a hub built
with it.

There are no tagged releases and nothing is published to PyPI. Hubs install both
packages from git and call the workflows at `@main`, so a change merged here
reaches every hub on its next build.

## Starting a hub

[example/](example/) is a complete minimal hub. Copying it is the quickest
start. A hub repository contains:

| Path | Needed for | Purpose |
|---|---|---|
| `hub.yaml` | site | Title, organization, theme, output toggles |
| `skills/<group>/group.yaml` | group labels | Label, description, and an optional integer `order` that sorts the group ahead of unordered (alphabetical) ones. Without it the group still builds, with a title-cased id and no description |
| `skills/<group>/<skill>/SKILL.md` | everything | YAML frontmatter plus the instructions the agent follows |
| `skills/<group>/<skill>/README.md` | guide | How to use the skill, written for the person installing it. Packaged, and shown above the instructions on the skill's page |
| `skills/<group>/<skill>/_hub/metadata.yaml` | card text | `summary`: one sentence for people browsing the site. Cards fall back to the agent-facing `description` without it |
| `skills/<group>/<skill>/_hub/rubric.yaml` | evaluation | Criteria, anti-patterns, scenarios. Only this location is read as a rubric |
| `templates/meta-skill.md` | meta skill bodies | A wrapper every meta skill is composed into. Without it, a meta `SKILL.md` keeps its own body and its `{{ bundled_skills }}` placeholder is expanded in place |
| `skills/<skill>/SKILL.md` | `outputs.suite_bundle` | A hub-level skill outside any group, such as an orientation; bundled first, with `{{ suite_skills }}` expanded |
| `templates/mcpb/` | `outputs.claude_extension` | The extension's own files, with `manifest.json` at the root |
| `eval.yaml` | evaluation | Models under test, judge models, API base URL |
| `tests/test_skills.py` | evaluation | One line: `from skill_eval.test_skills import *` |
| `.github/workflows/deploy.yml` | deployment | One job calling `harvard-lil/skills-hub/.github/workflows/build-and-deploy.yml@main` |

Everything in a skill directory goes into the skill's package except `_hub/`,
which holds files only the hub reads. A skill whose `name` ends in `-meta` is its
group's router: its package bundles the group's other skills. The full
discovery rules are in
[`discover.py`](packages/skills-hub-builder/src/skills_hub_builder/discover.py)
and summarized in [docs/commitments.md](docs/commitments.md).

GitHub Pages has to be enabled on the hub repository with Source set to GitHub
Actions. The deploy workflow cannot turn it on.

## `skills-hub-builder`

Generates the site. Run in a hub repository:

```bash
uvx --from git+https://github.com/harvard-lil/skills-hub#subdirectory=packages/skills-hub-builder skills-hub-builder build
```

It writes `_site/`:

- `index.html`, `css/`, `js/`: the index page. It loads the inventory JSON in
  the browser and renders a card per group and skill.
- `skills/<group>/<name>.skill`: a zip per skill and per meta skill.
- `skills/<group>/<name>.html`: a page per skill showing the skill's guide, if it
  has one, then the `SKILL.md` it would install. Skills with `status: draft` are
  marked as unreviewed here and on their cards; `status: official` is the
  reviewed state.
  A hub's `website/_skill_note.html`, if present, is rendered on every skill
  page under the guide, for example to link a page of general advice; the
  bundled one is empty.
- `inventory/groups.json`, `inventory/<group>.json`: the data the index page
  reads, published for agents to read too.
- `install.html`: a generic page on installing a `.skill` in an agent. It shows
  one-click cards only when `--custom-gpt-url` or a built `.mcpb` provides them.
  A hub's `website/install.html` replaces it, and `theme.exclude` can drop it.
- `traces/`: copied from the hub's `traces/` directory if present. No page in the
  bundled theme displays them; a hub that wants a trace index supplies
  `website/traces/index.html`.

Three more outputs are off unless `hub.yaml` turns them on:

- `outputs.suite_bundle` writes one install for every skill in the hub:
  `bundle/<name>.zip`, a plugin directory (`.claude-plugin/plugin.json` and
  `skills/<skill>/` for every non-meta skill) that claude.ai and the Claude
  desktop app accept through Upload plugin; `marketplace.json`, a Claude Code
  plugin marketplace listing that zip as an `archive` source; and
  `.well-known/agent-skills/index.json`, the index the `skills` CLI reads from
  the site URL. `install.html` gains an "Install everything" section. A skill
  directly under `skills/`, outside any group, is a hub-level skill: it leads the
  bundle, is also written as `skills/<name>.skill`, and its `{{ suite_skills }}`
  placeholder becomes a listing of every other skill. Names come from an optional
  `suite:` block (`name`, `marketplace`, `display_name`, `description`,
  `version`), defaulting to a slug of the site title. See
  [docs/adr/2026-10-28-suite-bundle.md](docs/adr/2026-10-28-suite-bundle.md).

- `outputs.gpt_actions` writes `actions/`: `openapi.json`, `openapi.yaml`, and a
  JSON file per group, skill, and skill reference, for a ChatGPT Custom GPT to
  fetch as plain GETs. These files call a group a `persona`.
- `outputs.claude_extension` writes `packages/mcpb/<name>.mcpb`, zipped from the
  hub's `templates/mcpb/` with `{{base_url}}`, `{{personas_json}}` and
  `{{personas_summary}}` substituted. `<name>` comes from the hub's
  `manifest.json`; the builder supplies no extension files of its own.

## `skill-eval`

An LLM-as-judge harness. For each skill's `_hub/rubric.yaml`, it plays the
rubric's scripted user turns against each model under test, with the `SKILL.md`
as system prompt. A judge model then scores the transcript against the rubric,
and the harness writes a JSON trace to `traces/`. Each scenario also runs against
the bare model with no skill, recorded as version `_null`, as a baseline.

```bash
uvx --from git+https://github.com/harvard-lil/skills-hub#subdirectory=packages/skill-eval skill-eval run
```

Runs call a paid API. The default configuration uses OpenRouter and reads
`OPENROUTER_API_KEY`; without a key, the evaluation tests skip.

## Developing this repository

```
packages/skills-hub-builder/   site generator and packager
packages/skill-eval/           evaluation harness
actions/                       composite actions (build, eval)
.github/workflows/             reusable workflows that hubs call, and this repo's CI
skills/hub-setup/              this repository's own skills, for setting up a hub
hub.yaml                       builds those skills as a hub
example/                       minimal example hub
docs/                          commitments, decisions, roadmap, research, guides
```

This repository builds its own `skills/hub-setup/` as a hub. A change that
breaks the hub contract therefore breaks `just build-self` as well as
`just build-example`.

`just --list` shows all recipes. The common ones:

| Recipe | What it does |
|---|---|
| `just dev` | `uv sync --all-packages` |
| `just test` | Both packages' unit tests; no network access |
| `just lint` / `just fmt` | Ruff check / format over `packages/` |
| `just build-example` | Build `example/` into `example/_site` |
| `just build-self` | Build this repository's hub into `_site` |
| `just inspect-example` | Print the skill tree discovered in `example/` |
| `just discover-example` | List the example's rubrics and scenarios |
| `just clean` | Remove `_site` and `example/_site` |

CI runs `just lint`, `just test`, `just build-example` and `just build-self` on
every pull request and on pushes to `main`. The unit tests cover the builder and
the harness's own code; they do not judge any skill's quality, and they do not
call a model.

## Documentation

- [AGENTS.md](AGENTS.md): rules for changing this repository
- [docs/commitments.md](docs/commitments.md): the hub contract, checked facts,
  known gaps, and what is deliberately out of scope
- [docs/adr/](docs/adr/): why the structure is what it is
- [docs/roadmap.md](docs/roadmap.md): what is next and what is unresolved
- [docs/research/](docs/research/): checked evidence, with dates
- [docs/guides/](docs/guides/): writing skills and their metadata, and running user tests
