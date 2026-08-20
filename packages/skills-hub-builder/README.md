# skills-hub-builder

Static site generator for publishing curated collections of AI agent skills. Given a `skills/` directory with markdown skill files, produces a browsable website with download links, inventory APIs, and packaged `.skill` files.

## Usage

```bash
# Install from git
pip install "skills-hub-builder @ git+https://github.com/harvard-lil/skills-hub#subdirectory=packages/skills-hub-builder"

# Or run with uvx
uvx --from "git+https://github.com/harvard-lil/skills-hub#subdirectory=packages/skills-hub-builder" skills-hub-builder build

# Build from a specific project directory
skills-hub-builder build --project /path/to/project --base-url https://org.github.io/repo/
```

## Project Structure

Your project needs:

```
my-skills-hub/
├── hub.yaml            # Site config (title, org, theme)
├── skills/
│   ├── group-a/
│   │   ├── group.yaml  # Group metadata
│   │   └── skill-one/
│   │       └── SKILL.md
│   └── group-b/
│       ├── group.yaml
│       └── skill-two/
│           └── SKILL.md
└── website/            # Optional template overrides
```
