# Data Monitoring Toolkit — Example

This is a minimal example of a project that uses [skills-hub-builder](../packages/skills-hub-builder/) to publish a collection of AI agent skills as a static website.

It is also the executable statement of what a consumer repository must provide:
every file below is one a real hub needs, and nothing here is decoration. A
change to the consumer contract that does not change this directory is
incomplete. See [../docs/commitments.md](../docs/commitments.md) for the contract
in prose. The skills here exist to give the builder something real to discover
and package. The hub they imitate is a separate repository — `pubdata-skills`,
which uses the same title and four groups of its own — so treat anything in
`skills/` here as a fixture rather than as content to copy.

## Quick Start

```bash
# Build the site locally
uvx --from ../packages/skills-hub-builder skills-hub-builder build

# Inspect the discovered skill tree
uvx --from ../packages/skills-hub-builder skills-hub-builder inspect

# Run evaluations (requires OPENROUTER_API_KEY in .env)
uvx --from ../packages/skill-eval skill-eval run
```

## Structure

```
.
├── hub.yaml                    # Site configuration
├── eval.yaml                   # Evaluation config (models, API)
├── skills/
│   ├── risk-assessment/        # Group: Data Risk Assessment
│   │   ├── group.yaml          # Group metadata
│   │   ├── risk-assessment-meta/
│   │   │   └── SKILL.md        # Meta-skill (router)
│   │   └── analyzing-data-risk/
│   │       ├── SKILL.md        # Skill instructions
│   │       ├── rubric.yaml     # Evaluation rubric
│   │       └── references/     # Supporting documents
│   │           └── risk-rubric.md
│   └── monitoring/             # Group: Dataset Monitoring
│       ├── group.yaml
│       └── binoc-diffs/
│           └── SKILL.md
├── tests/
│   └── test_skills.py          # Re-exports generic tests
└── .github/workflows/
    └── deploy.yml              # One-line deployment workflow
```

## Deployment

Push to `main` and the GitHub Action builds the site and deploys to Pages automatically.
