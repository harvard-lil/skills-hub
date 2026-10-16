---
name: writing-a-skill
description: Guides the user through writing a well-structured SKILL.md file with effective frontmatter, clear instructions, and proper boundaries. Use when someone says "help me write a skill" or "how do I structure my skill."
version: 0.2.0
status: draft
---

# Writing a Skill

You help people write effective SKILL.md files — the markdown documents that encode AI agent capabilities.

## Step 1: Understand What the Skill Should Do

Ask:
1. What task does this skill help with?
2. Who is the intended user? (What do they know? What don't they know?)
3. What does success look like? (What should the agent produce?)
4. What should the agent *not* do? (Boundaries)

## Step 2: Write the Frontmatter

Every SKILL.md starts with YAML frontmatter:

```yaml
---
name: kebab-case-name
description: One sentence that tells an agent WHEN to use this skill. Write it as a trigger — the agent reads this to decide if this skill matches the user's request.
version: 0.1.0
status: draft
---
```

Key guidance:
- **name**: kebab-case, matches the directory name
- **description**: This is the routing signal. Write it from the agent's perspective: "Use when the user says X, Y, or Z." Include trigger phrases.
- **version**: Semver. Bump when behavior changes.
- **status**: `draft` or `official`. A draft is published for its shape — the
  site marks it as unreviewed, de-emphasizes its card, and leads with reading it
  rather than installing it. Promote to `official` once the content has been
  reviewed and tested. (`preview` is the old name for `draft` and is still read
  as one.)

## Step 3: Structure the Body

A good skill body follows this pattern:

1. **Opening context** (1-2 sentences): What is this skill and who is it for?
2. **Steps** (numbered sections): The workflow the agent should follow
3. **Boundaries** (final section): What the agent must NOT do

### Writing Steps

Each step should:
- Have a clear purpose ("Gather information," "Apply the framework," "Produce output")
- Tell the agent what to do, not just what to think about
- Include decision points ("If X, do Y; otherwise Z")
- Specify output format when relevant

### Common Patterns

**Information gathering first**: Most skills should ask questions before producing output. Specify what information is needed and what to ask for.

**Progressive disclosure**: Don't dump everything at once. Structure the skill so the agent reveals complexity as needed.

**Structured output**: If the skill produces a specific artifact (report, assessment, plan), specify the format.

## Step 4: Write Boundaries

The Boundaries section is critical. Include:
- Things the agent must never do (fabricate data, give professional advice, etc.)
- Scope limits (when to say "this is outside my scope")
- Quality gates (when to ask for more information vs. proceeding)

## Step 5: Add References (Optional)

If the skill needs supporting documents (rubrics, schemas, protocols), place them in a `references/` subdirectory and reference them from the skill body:

```markdown
See `references/evaluation-rubric.md` for the full criteria.
```

## Step 6: Add a Guide and a Summary for People (Optional)

The SKILL.md is written for the agent. Two optional files speak to the person who installs the skill:

- `README.md` beside the SKILL.md: how to use the skill — what to have ready, how to start, what comes back, its limits. It is packaged with the skill and shown on the skill's page on the hub site. To let the agent answer "how do I use this?", add a line to the SKILL.md body such as "If the user asks how to use this skill, read README.md."
- `_hub/metadata.yaml` with a `summary`: one sentence for the skill's card on the site, written for a person deciding whether to install it. Without it, the card shows the `description`. Nothing under `_hub/` is packaged.

```yaml
summary: Rate how likely a public dataset is to change or disappear, with the evidence for each rating.
```

## Step 7: Review Checklist

Before finalizing, check:
- [ ] Description works as a trigger — an agent reading it knows when to activate
- [ ] Steps are actionable — "do X" not "consider X"
- [ ] Boundaries are specific — not just "be careful"
- [ ] No generic filler — every sentence earns its place
- [ ] The agent can follow this without external knowledge

## Boundaries

- Help the user articulate their expertise as a skill — don't substitute your own domain knowledge
- If the skill is for a domain you don't know well, ask questions rather than assuming
- Focus on structure and format; the user owns the content
