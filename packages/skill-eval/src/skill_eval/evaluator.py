"""Evaluate a conversation trace against a rubric using LLM judges.

Criteria types:
- Structural: binary pass/fail checks on observable behavior
- Qualitative: three-level ratings (strong/adequate/weak) on subjective dimensions
- Anti-patterns: binary violation checks (any violation = overall failure)

Each criterion is evaluated independently in its own LLM call for
narrow, debuggable judgments.
"""

from __future__ import annotations

import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import Enum

from openai import OpenAI

from .runner import ConversationTrace, ModelConfig

MAX_EVAL_WORKERS = 10

log = logging.getLogger("skill_eval.evaluator")


class StructuralResult(Enum):
    PASS = "pass"
    FAIL = "fail"


class QualitativeRating(Enum):
    STRONG = "strong"
    ADEQUATE = "adequate"
    WEAK = "weak"


class AntiPatternResult(Enum):
    CLEAR = "clear"
    VIOLATION = "violation"


@dataclass
class CriterionEval:
    """Result of evaluating a single criterion."""

    criterion_id: str
    description: str
    result: str
    justification: str


@dataclass
class EvaluationReport:
    """Complete evaluation of a conversation against a rubric."""

    skill_name: str
    scenario_id: str
    model_id: str
    judge_model_id: str
    structural: list[CriterionEval] = field(default_factory=list)
    qualitative: list[CriterionEval] = field(default_factory=list)
    anti_patterns: list[CriterionEval] = field(default_factory=list)

    # Internal: qualitative criteria metadata for scoring
    _qual_criteria_meta: list[dict] = field(default_factory=list, repr=False)

    def structural_pass_count(self) -> int:
        return sum(1 for c in self.structural if c.result == StructuralResult.PASS.value)

    def has_anti_pattern_violations(self) -> bool:
        return any(c.result == AntiPatternResult.VIOLATION.value for c in self.anti_patterns)

    def score(self) -> float:
        """Compute a 0-100 score.

        Formula:
        - Structural: (passed / total) * 40 points
        - Qualitative: weighted average of ratings * 40 points
        - Base: 20 points
        - Anti-pattern penalty: -20 per violation
        """
        if not self.structural and not self.qualitative:
            return 0.0

        # Structural score
        structural_total = len(self.structural)
        structural_score = (
            (self.structural_pass_count() / structural_total * 40)
            if structural_total
            else 20.0
        )

        # Qualitative score
        weight_map = {"high": 3, "medium": 2, "low": 1}
        rating_values = {
            QualitativeRating.STRONG.value: 1.0,
            QualitativeRating.ADEQUATE.value: 0.6,
            QualitativeRating.WEAK.value: 0.2,
        }

        if not self.qualitative:
            qual_score = 20.0
        else:
            meta_by_id = {c["id"]: c for c in self._qual_criteria_meta}
            total_weight = 0
            weighted_sum = 0.0
            for c in self.qualitative:
                meta = meta_by_id.get(c.criterion_id, {})
                w = weight_map.get(meta.get("weight", "medium"), 2)
                total_weight += w
                weighted_sum += w * rating_values.get(c.result, 0.4)
            qual_score = (weighted_sum / total_weight * 40) if total_weight else 20.0

        # Anti-pattern penalty
        violation_count = sum(
            1 for c in self.anti_patterns
            if c.result == AntiPatternResult.VIOLATION.value
        )
        penalty = min(violation_count * 20, 100)

        return max(0.0, structural_score + qual_score + 20 - penalty)

    def summary(self) -> str:
        lines = [
            f"Skill: {self.skill_name} | Scenario: {self.scenario_id}",
            f"Model: {self.model_id} | Judge: {self.judge_model_id}",
            f"Score: {self.score():.0f}/100",
            "",
            f"Structural: {self.structural_pass_count()}/{len(self.structural)} pass",
        ]
        for c in self.structural:
            status = "PASS" if c.result == StructuralResult.PASS.value else "FAIL"
            lines.append(f"  [{status}] {c.criterion_id}: {c.justification}")

        lines.append("")
        lines.append("Qualitative:")
        for c in self.qualitative:
            lines.append(f"  [{c.result.upper()}] {c.criterion_id}: {c.justification}")

        violations = [c for c in self.anti_patterns if c.result == AntiPatternResult.VIOLATION.value]
        lines.append("")
        if violations:
            lines.append(f"Anti-pattern violations: {len(violations)}")
            for c in violations:
                lines.append(f"  [VIOLATION] {c.criterion_id}: {c.justification}")
        else:
            lines.append("Anti-patterns: all clear")

        return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────
# Judge prompts
# ──────────────────────────────────────────────────────────────────────

STRUCTURAL_PROMPT = """\
You are evaluating a conversation between an AI agent and a user. The agent has a skill installed.

Evaluate this specific criterion:
ID: {criterion_id}
Description: {description}
How to check: {check}

Conversation transcript:
{transcript}

Does the agent's behavior satisfy this criterion? Respond with exactly this JSON format:
{{"result": "pass" or "fail", "justification": "<one sentence explaining your judgment>"}}"""

QUALITATIVE_PROMPT = """\
You are evaluating a conversation between an AI agent and a user. The agent has a skill installed.

Evaluate this specific quality dimension:
ID: {criterion_id}
Description: {description}

Conversation transcript:
{transcript}

Rate the agent on this dimension. Respond with exactly this JSON format:
{{"result": "strong" or "adequate" or "weak", "justification": "<one sentence explaining your judgment>"}}"""

ANTI_PATTERN_PROMPT = """\
You are evaluating a conversation between an AI agent and a user. The agent has a skill installed.

Check for this anti-pattern:
ID: {criterion_id}
Description: {description}
How to detect: {check}

Conversation transcript:
{transcript}

Did the agent violate this anti-pattern? Respond with exactly this JSON format:
{{"result": "clear" or "violation", "justification": "<one sentence explaining your judgment>"}}"""


# ──────────────────────────────────────────────────────────────────────
# Evaluation logic
# ──────────────────────────────────────────────────────────────────────

def _parse_judge_response(text: str) -> dict:
    """Extract JSON from the judge's response, handling markdown fences."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def _evaluate_criterion(
    client: OpenAI,
    judge: ModelConfig,
    prompt_template: str,
    criterion: dict,
    transcript: str,
    category: str = "",
) -> CriterionEval:
    """Evaluate a single criterion using the judge model."""
    log.debug("  Judging %s [%s] with %s ...", criterion["id"], category, judge.model)
    prompt = prompt_template.format(
        criterion_id=criterion["id"],
        description=criterion["description"],
        check=criterion.get("check", criterion["description"]),
        transcript=transcript,
    )

    response = client.chat.completions.create(
        model=judge.model,
        messages=[{"role": "user", "content": prompt}],
        temperature=judge.temperature,
        max_tokens=judge.max_tokens,
    )

    raw = response.choices[0].message.content or "{}"
    try:
        parsed = _parse_judge_response(raw)
    except (json.JSONDecodeError, KeyError):
        log.warning("  Judge response unparseable for %s: %s", criterion["id"], raw[:200])
        parsed = {"result": "fail", "justification": f"Judge response unparseable: {raw[:200]}"}

    result = parsed.get("result", "fail")
    justification = parsed.get("justification", "No justification provided")
    tag = result.upper()
    log.info("  [%s] %s %s — %s", tag, category, criterion["id"], justification)

    return CriterionEval(
        criterion_id=criterion["id"],
        description=criterion["description"],
        result=result,
        justification=justification,
    )


def evaluate_trace(
    client: OpenAI,
    judge: ModelConfig,
    rubric: dict,
    trace: ConversationTrace,
) -> EvaluationReport:
    """Evaluate a conversation trace against a rubric using the judge model.

    The rubric dict should have 'criteria' (with 'structural' and 'qualitative'
    lists) and 'anti_patterns' keys.
    """
    transcript = trace.as_transcript()
    criteria = rubric.get("criteria", {})
    structural = criteria.get("structural", [])
    qual_criteria = criteria.get("qualitative", criteria.get("pedagogical", []))
    anti_patterns = rubric.get("anti_patterns", [])

    total_checks = len(structural) + len(qual_criteria) + len(anti_patterns)
    log.info(
        "Evaluating %s::%s with judge %s (%d criteria)",
        trace.skill_name, trace.scenario_id, judge.model, total_checks,
    )

    report = EvaluationReport(
        skill_name=trace.skill_name,
        scenario_id=trace.scenario_id,
        model_id=trace.model_id,
        judge_model_id=judge.id,
        _qual_criteria_meta=qual_criteria,
    )

    with ThreadPoolExecutor(max_workers=MAX_EVAL_WORKERS) as executor:
        structural_futures = [
            executor.submit(
                _evaluate_criterion, client, judge, STRUCTURAL_PROMPT,
                c, transcript, "structural",
            )
            for c in structural
        ]
        qualitative_futures = [
            executor.submit(
                _evaluate_criterion, client, judge, QUALITATIVE_PROMPT,
                c, transcript, "qualitative",
            )
            for c in qual_criteria
        ]
        anti_pattern_futures = [
            executor.submit(
                _evaluate_criterion, client, judge, ANTI_PATTERN_PROMPT,
                c, transcript, "anti-pattern",
            )
            for c in anti_patterns
        ]

        report.structural = [f.result() for f in structural_futures]
        report.qualitative = [f.result() for f in qualitative_futures]
        report.anti_patterns = [f.result() for f in anti_pattern_futures]

    log.info("  Score: %.0f/100", report.score())
    return report
