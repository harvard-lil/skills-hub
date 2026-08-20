# Distribute to consumers from `@main`

- Status: Accepted
- Recorded: 2026-08-20, from the code as it stands

## Context

Consumers need the builder and the harness at CI time, and they need the
deployment steps. Both packages are at `0.1.0` with no tag and no release.

## Decision

Consumers get everything from git at `main`:

- `.github/workflows/build-and-deploy.yml@main` as a reusable workflow, called
  as a consumer's whole CI;
- `uv pip install "skills-hub-builder @ git+https://github.com/harvard-lil/skills-hub#subdirectory=packages/skills-hub-builder"`
  inside that workflow, and the equivalent for `skill-eval`;
- `uvx --from git+...` for local runs.

No PyPI publication, no version pinning on the consumer side. The workflow derives
`base-url` and `repo-url` from `GITHUB_REPOSITORY` so a consumer's deploy job has
no required inputs at all.

## Alternatives considered

**Publish to PyPI and pin versions.** Consumers would get reproducible builds and
could upgrade deliberately. It also adds a release step to every fix and lets
consumers drift apart, which is the failure the extraction was meant to end.

**Vendor the builder into each consumer.** Reproducible and inspectable, and it
recreates the copies the extraction removed.

**Tag releases and have consumers reference `@v1`.** The middle option: a moving
target that only moves on purpose. Available later without changing the consumer
contract, since only the ref changes.

## Consequences

- A push to `main` here changes every consumer's next build. There is no release
  to hide behind, which is why `AGENTS.md` treats the workflows and `actions/` as
  published interface.
- A consumer cannot reproduce an old build. `_site` is a function of `main` at
  build time, not of anything recorded in the consumer's repository.
- Version numbers in `packages/*/pyproject.toml` carry no distribution meaning
  today. They document intent for whoever adopts tagging.
- Every consumer build installs from git, which needs network access to GitHub
  and no other package index credential.
