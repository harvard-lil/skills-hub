# Evaluate with an LLM judge and a null baseline

- Status: Accepted
- Recorded: 2026-08-20, from the code as it stands

## Context

A skill is instructions to a model. Whether it works is a question about model
behavior, and most of what a skill is supposed to produce — asking before
answering, refusing to write the user's work for them, grounding a claim in what
the user actually said — cannot be checked by string matching.

The behavior is also non-deterministic. Two runs of the same scenario differ, so
a single run cannot decide whether a change helped.

## Decision

Replay scripted conversations and have a judge model score the transcript.
Per `runner.py`, `evaluator.py`, and `trace_writer.py`:

- a `rubric.yaml` beside a `SKILL.md` defines structural criteria (binary),
  qualitative criteria (strong/adequate/weak, weighted), anti-patterns (binary,
  penalised), and scenarios of scripted user turns;
- the skill is sent as the system prompt and the user turns are replayed in
  order, with the model's own replies fed back;
- each criterion is judged in its own model call, so a judgment is narrow and its
  justification is attributable;
- a score is composed as 20 base + 40 structural + 40 qualitative, minus 20 per
  anti-pattern violation, and the suite fails below 50 or on any violation;
- every run writes a JSON trace under
  `traces/<group>/<skill>/<version>/<scenario>_<seq>.json`, sequence-numbered so
  runs accumulate, and the traces are committed to the consumer's repository;
- each scenario also runs with the system prompt replaced by "You are a helpful
  assistant.", stored under version `_null` with a minimum score of 0, so it
  records without ever failing the suite.

The harness runs under pytest, so a consumer's `tests/test_skills.py` is one
re-export line and discovery, parametrization, and fixtures come from the
installed plugin.

## Alternatives considered

**Deterministic assertions on model output.** Cheap, reproducible, and unable to
express the criteria that matter. It would test formatting and miss pedagogy.

**Human review only.** The most trustworthy signal, and the one that does not
scale to a rubric per skill per revision. It remains the right check before
adopting a skill; the harness is for noticing change between reviews.

**Score the whole transcript in one judge call.** Fewer API calls and cheaper.
It also produces one number whose reasons cannot be separated, so a regression
cannot be attributed to a criterion.

**Discard traces after asserting.** Would make the suite a pass/fail gate. Keeping
them, and keeping the skill-less baseline beside them, is what allows the
question "is this skill adding anything" to be asked at all.

## Consequences

- The suite is not a gate anyone should trust. The 50-point floor catches a model
  that ignored the skill; it does not certify quality, and the same input can
  land on either side of it.
- Running it costs money and needs `OPENROUTER_API_KEY`. Without a key the
  fixtures skip, so a consumer's CI stays green having evaluated nothing.
- Traces accumulate in consumers' repositories indefinitely. Nothing prunes them.
- The judge shares the API client, and by default the model family, with the
  system under test. Whether that biases scores has not been examined here.
- `trace_exists` skips a scenario that already has a trace for the same skill,
  version, scenario, and model. Editing a `SKILL.md` without bumping its version
  leaves the old trace in place and the new behavior unmeasured.
