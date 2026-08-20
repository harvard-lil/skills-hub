---
name: writing-a-rubric
description: Guides the user through creating a rubric.yaml evaluation file for testing whether a skill works well. Use when someone says "how do I test my skill," "write a rubric," or "set up evaluation."
version: 0.1.0
status: preview
---

# Writing a Rubric

You help people create rubric.yaml files — structured evaluation criteria that test whether a skill is working well. Rubrics enable automated LLM-as-judge testing and quality trending over time.

## Step 1: Read the Skill

Ask the user to provide or point to the SKILL.md they want to evaluate. Read it carefully and identify:
- The defined steps and workflow
- The boundaries (things the agent must NOT do)
- The expected outputs
- The persona/group constraints

## Step 2: Design Structural Criteria

Structural criteria answer "did the agent do X?" They're binary (pass/fail) and should be observable in the conversation transcript.

Good structural criteria:
- "Agent asks at least one clarifying question before producing output"
- "Agent produces a markdown table in its final response"
- "Agent references the evaluation framework by name"

Bad structural criteria (too vague):
- "Agent is helpful" (not observable)
- "Agent follows the skill" (too broad)

For each criterion, write:
```yaml
- id: kebab-case-id
  description: What the agent should do
  check: How to verify it — describe the observable behavior
```

## Step 3: Design Qualitative Criteria

Qualitative criteria answer "how well did the agent do X?" They're rated strong/adequate/weak and require judgment.

Good qualitative criteria:
- "Agent explains reasoning clearly and specifically rather than generically"
- "Agent adapts its approach based on user-provided context"

For each criterion, write:
```yaml
- id: kebab-case-id
  description: What quality looks like for this dimension
  weight: high | medium | low
```

Weight guide:
- **high**: Core to the skill's purpose. Failure here means the skill isn't working.
- **medium**: Important for quality but not essential for basic function.
- **low**: Nice to have. Polish and refinement.

## Step 4: Identify Anti-Patterns

Anti-patterns come from three sources:
1. **Group constraints**: The group's `design.principles` that must never be violated
2. **Skill boundaries**: The "Boundaries" section of the SKILL.md
3. **Common AI failures**: Fabricating data, giving unauthorized advice, ignoring user input

```yaml
- id: kebab-case-id
  description: What the agent must never do
  check: How to detect a violation in the transcript
```

## Step 5: Write Test Scenarios

Good scenarios cover:
- **Happy path**: Straightforward use case
- **Minimal input**: User provides little context — does the skill gather what it needs?
- **Boundary test**: User asks something adjacent but outside scope
- **Edge case**: Unusual situation that tests robustness

```yaml
- id: kebab-case-id
  setup: Context about the simulated user's situation
  messages:
    - role: user
      content: "What the user says"
    - role: user
      content: "Follow-up message"
  expected:
    - Agent does X
    - Agent does not do Y
```

Key rules:
- Messages are ONLY user messages (agent responses are captured during testing)
- Expected describes behaviors, not exact text
- Setup gives context to the test runner, not to the agent

## Step 6: Assemble

Produce the complete rubric.yaml:

```yaml
group: <group-id>
skill: <skill-name>

criteria:
  structural:
    - ...
  qualitative:
    - ...

anti_patterns:
  - ...

test_scenarios:
  - ...
```

## Step 7: Review

Check:
- [ ] Structural criteria are observable (not subjective)
- [ ] Qualitative criteria capture the skill's unique value
- [ ] Anti-patterns cover all boundaries stated in the skill
- [ ] Scenarios test different user situations (not just the happy path)
- [ ] Expected behaviors are specific enough to evaluate but not brittle

## Boundaries

- Help the user design evaluation criteria — don't evaluate skills yourself
- If you don't understand the skill's domain, ask questions
- Focus on testability and specificity, not comprehensiveness for its own sake
