# Separate hub infrastructure from hub content

- Status: Accepted
- Recorded: 2026-08-20, from the code as it stands

## Context

`lawskills-hub` was built as a single repository: legal education skills next to
`scripts/build.py`, `scripts/build_actions.py`, `scripts/build_mcpb.py`,
`templates/`, and `website/`. It works, and it publishes a site LIL is happy with.

LIL now wants more than one hub. `pubdata-skills` was created on 2026-08-19 for
the Public Data Project, and more are anticipated. Under the single-repository
shape, each new hub starts by copying build scripts, and every later fix has to
be applied in each copy.

The two halves also change at different rates and are edited by different people.
Skills are written by subject-matter experts who are not necessarily engineers —
the premise of `lawskills-hub`'s contributor guide. Build machinery is engineering
work, and a contributor writing a skill should not have to read it.

## Decision

Extract the build machinery into `skills-hub` as two installable packages plus
reusable GitHub Actions, and leave every hub's skills in its own repository. A
consumer repository holds `hub.yaml`, `skills/`, `eval.yaml`, `tests/`, and a
one-job workflow; it holds no build code.

Keep `example/` and this repository's own `skills/hub-setup/` here, so the
contract is exercised by two builds that run on every change.

## Alternatives considered

**Leave the machinery in `lawskills-hub` and have new hubs depend on it.** The
legal education repository would become an infrastructure dependency for
unrelated projects, and its contributor guide would have to address two audiences.

**Copy the scripts into each new hub.** No coordination cost up front, and no
shared fix afterwards. Reasonable for two hubs, poor for several.

**Publish only a Python library and let each hub write its own workflow.** Would
have left every consumer owning CI. Deployment is the part most likely to be
copied wrong, so it is the part most worth sharing.

## Consequences

- A change to the discovery rules, the inventory shape, or the workflows affects
  every consumer at once, which is the point and also the risk. See the interface
  rules in [../../AGENTS.md](../../AGENTS.md).
- The near-term test of the decision is whether `lawskills-hub` can be adapted to
  consume this repository without a visible change to its published site. That
  adaptation is in progress; the gaps found by reading both trees are in
  [../research/2026-08-20-lawskills-hub-parity.md](../research/2026-08-20-lawskills-hub-parity.md).
- `hub.yaml` carries `outputs.gpt_actions` and `outputs.claude_extension` flags
  that nothing reads. Reading the two trees together, these look like placeholders
  for `lawskills-hub`'s `build_actions.py` and `build_mcpb.py`, which have not
  been ported. That is an inference from the file names and the flag names; no
  statement of intent exists in the repository.
