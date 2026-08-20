---
name: writing-a-skill
description: Guides the user through writing a well-structured SKILL.md file with effective frontmatter, clear instructions, and proper boundaries. Use when someone says "help me write a skill" or "how do I structure my skill."
version: 0.1.0
status: preview
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
status: preview
---
```

Key guidance:
- **name**: kebab-case, matches the directory name
- **description**: This is the routing signal. Write it from the agent's perspective: "Use when the user says X, Y, or Z." Include trigger phrases.
- **version**: Semver. Bump when behavior changes.
- **status**: `preview` (experimental) or `official` (stable, tested)

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

## Step 6: Review Checklist

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
