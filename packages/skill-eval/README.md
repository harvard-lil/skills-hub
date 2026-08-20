# skill-eval

LLM-as-judge evaluation harness for AI agent skills. Runs scripted conversation scenarios against models, evaluates responses against rubrics with structural and qualitative criteria, and produces versioned traces for quality trending.

## Usage

```bash
# Install from git
pip install "skill-eval @ git+https://github.com/harvard-lil/skills-hub#subdirectory=packages/skill-eval"

# Or run with uvx
uvx --from "git+https://github.com/harvard-lil/skills-hub#subdirectory=packages/skill-eval" skill-eval discover

# Run evaluations
skill-eval run --project /path/to/your/project
```

## Rubric Format

Place a `rubric.yaml` next to any `SKILL.md` to define evaluation criteria:

```yaml
group: my-group
skill: my-skill

criteria:
  structural:
    - id: asks-questions
      description: Agent asks clarifying questions before acting
      check: Agent's first response contains a question

  qualitative:
    - id: clear-reasoning
      description: Agent explains its reasoning clearly
      weight: high

anti_patterns:
  - id: fabricates-info
    description: Agent invents information not provided by the user
    check: Agent makes specific factual claims without evidence

test_scenarios:
  - id: basic-usage
    setup: User has a straightforward request
    messages:
      - role: user
        content: "Help me with X"
    expected:
      - Agent asks for context
      - Agent provides structured response
```
