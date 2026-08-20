---
name: creating-a-hub
description: Walks the user through creating a new skills hub project from scratch — from repo setup through first deployment. Use when someone says "I want to publish a collection of skills" or "set up a new hub."
version: 0.1.0
status: preview
---

# Creating a Skills Hub

You walk the user through creating a new skills hub project from scratch. By the end, they'll have a working repository that builds and deploys a static site to GitHub Pages.

## Step 1: Understand the Domain

Ask the user:
1. What domain or audience are these skills for? (e.g., "data monitoring for librarians," "legal research for students")
2. How do they want to group their skills? (by task type, by audience, by tool, etc.)
3. Do they already have skills written, or are they starting fresh?

## Step 2: Create the Project Structure

Guide them through creating:

```
my-skills-hub/
├── hub.yaml
├── skills/
│   └── <first-group>/
│       ├── group.yaml
│       └── <first-skill>/
│           └── SKILL.md
└── .github/workflows/
    └── deploy.yml
```

### hub.yaml

```yaml
site:
  title: <Their Hub Name>
  subtitle: <One-line description>
  org_name: <Organization>
  org_url: <Org website>

nav:
  - label: Skills
    href: "#groups"
  - label: GitHub
    href: "{{ repo_url }}"
    external: true
```

### .github/workflows/deploy.yml

```yaml
name: Deploy
on:
  push:
    branches: [main]
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

jobs:
  build-and-deploy:
    uses: harvard-lil/skills-hub/.github/workflows/build-and-deploy.yml@main
```

## Step 3: Create the First Group

Help them write a `group.yaml`:

```yaml
label: <Human-readable name>
description: <What this group of skills does>
design:
  objective: <The goal these skills serve>
  principles:
    - <Guideline 1>
    - <Guideline 2>
  tone: <How the skills in this group should communicate>
```

## Step 4: Create the First Skill

Help them write their first `SKILL.md` with frontmatter and instructions. Refer them to the "writing-a-skill" skill if they need detailed guidance on skill authoring.

## Step 5: Deploy

1. Create a GitHub repository
2. Enable GitHub Pages (Settings → Pages → Source: GitHub Actions)
3. Push the code
4. The workflow runs automatically on push to main

## Step 6: Iterate

Explain that adding more skills is just:
1. Create a new directory under the appropriate group
2. Add a SKILL.md
3. Push

The site rebuilds automatically.

## Boundaries

- Don't write the user's skills for them (that's a different skill)
- Focus on the infrastructure and project setup
- If they want custom styling, explain the `website/` override pattern
