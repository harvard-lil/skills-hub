"""Tests for the LLM-as-judge evaluator."""

import json
from unittest.mock import MagicMock, patch

from skill_eval.evaluator import (
    AntiPatternResult,
    CriterionEval,
    EvaluationReport,
    QualitativeRating,
    StructuralResult,
    _parse_judge_response,
    evaluate_trace,
)
from skill_eval.runner import ConversationTrace, Message, ModelConfig


class TestParseJudgeResponse:
    def test_plain_json(self):
        result = _parse_judge_response('{"result": "pass", "justification": "looks good"}')
        assert result["result"] == "pass"

    def test_markdown_fenced(self):
        text = '```json\n{"result": "fail", "justification": "nope"}\n```'
        result = _parse_judge_response(text)
        assert result["result"] == "fail"

    def test_no_language_tag(self):
        text = '```\n{"result": "strong", "justification": "yes"}\n```'
        result = _parse_judge_response(text)
        assert result["result"] == "strong"


class TestEvaluationReport:
    def _make_report(self, structural=None, qualitative=None, anti_patterns=None):
        return EvaluationReport(
            skill_name="test",
            scenario_id="s1",
            model_id="m",
            judge_model_id="j",
            structural=structural or [],
            qualitative=qualitative or [],
            anti_patterns=anti_patterns or [],
            _qual_criteria_meta=[
                {"id": "q1", "weight": "high"},
                {"id": "q2", "weight": "low"},
            ],
        )

    def test_score_all_pass_strong(self):
        report = self._make_report(
            structural=[
                CriterionEval("s1", "d", "pass", "ok"),
                CriterionEval("s2", "d", "pass", "ok"),
            ],
            qualitative=[
                CriterionEval("q1", "d", "strong", "great"),
                CriterionEval("q2", "d", "strong", "great"),
            ],
        )
        # structural: 2/2 * 40 = 40
        # qualitative: (3*1 + 1*1) / (3+1) * 40 = 40
        # base: 20
        assert report.score() == 100.0

    def test_score_all_fail_weak(self):
        report = self._make_report(
            structural=[
                CriterionEval("s1", "d", "fail", "bad"),
            ],
            qualitative=[
                CriterionEval("q1", "d", "weak", "poor"),
            ],
        )
        # structural: 0/1 * 40 = 0
        # qualitative: (3*0.2) / 3 * 40 = 8
        # base: 20
        assert report.score() == 28.0

    def test_score_anti_pattern_penalty(self):
        report = self._make_report(
            structural=[CriterionEval("s1", "d", "pass", "ok")],
            qualitative=[CriterionEval("q1", "d", "strong", "great")],
            anti_patterns=[CriterionEval("ap1", "d", "violation", "bad")],
        )
        base_score = 40 + 40 + 20  # would be 100
        assert report.score() == 80.0  # -20 penalty

    def test_has_anti_pattern_violations(self):
        report = self._make_report(
            anti_patterns=[CriterionEval("ap1", "d", "violation", "bad")],
        )
        assert report.has_anti_pattern_violations() is True

    def test_no_violations(self):
        report = self._make_report(
            anti_patterns=[CriterionEval("ap1", "d", "clear", "fine")],
        )
        assert report.has_anti_pattern_violations() is False

    def test_summary(self):
        report = self._make_report(
            structural=[CriterionEval("s1", "d", "pass", "ok")],
        )
        summary = report.summary()
        assert "test" in summary
        assert "Score:" in summary
        assert "1/1 pass" in summary


class TestEvaluateTrace:
    def test_evaluate_calls_judge_per_criterion(self, sample_trace, sample_rubric, judge_config):
        """Each criterion gets its own judge call."""
        client = MagicMock()

        def make_judge_response(*args, **kwargs):
            resp = MagicMock()
            resp.choices = [MagicMock()]
            resp.choices[0].message.content = json.dumps({
                "result": "pass",
                "justification": "Looks good",
            })
            return resp

        client.chat.completions.create.side_effect = make_judge_response

        report = evaluate_trace(client, judge_config, sample_rubric, sample_trace)

        # 2 structural + 1 qualitative + 1 anti-pattern = 4 calls
        assert client.chat.completions.create.call_count == 4
        assert len(report.structural) == 2
        assert len(report.qualitative) == 1
        assert len(report.anti_patterns) == 1

    def test_evaluate_handles_unparseable_response(self, sample_trace, sample_rubric, judge_config):
        client = MagicMock()
        resp = MagicMock()
        resp.choices = [MagicMock()]
        resp.choices[0].message.content = "I'm not JSON at all!"
        client.chat.completions.create.return_value = resp

        report = evaluate_trace(client, judge_config, sample_rubric, sample_trace)

        # Should not crash — unparseable responses become "fail"
        assert all(c.result == "fail" for c in report.structural)

    def test_evaluate_supports_pedagogical_alias(self, sample_trace, judge_config):
        """'pedagogical' is accepted as an alias for 'qualitative' in rubrics."""
        rubric = {
            "criteria": {
                "structural": [],
                "pedagogical": [
                    {"id": "p1", "description": "teaches well", "weight": "medium"},
                ],
            },
            "anti_patterns": [],
        }

        client = MagicMock()
        resp = MagicMock()
        resp.choices = [MagicMock()]
        resp.choices[0].message.content = '{"result": "strong", "justification": "good"}'
        client.chat.completions.create.return_value = resp

        report = evaluate_trace(client, judge_config, rubric, sample_trace)
        assert len(report.qualitative) == 1
        assert report.qualitative[0].result == "strong"
