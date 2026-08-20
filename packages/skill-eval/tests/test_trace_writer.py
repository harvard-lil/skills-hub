"""Tests for trace writing and indexing."""

import json
from pathlib import Path

from skill_eval.evaluator import CriterionEval, EvaluationReport
from skill_eval.runner import ConversationTrace, Message, ModelConfig
from skill_eval.trace_writer import rebuild_index, save_trace, trace_exists


def _make_trace_and_report():
    trace = ConversationTrace(
        skill_name="my-skill",
        scenario_id="scenario-1",
        model_id="test-model",
        messages=[
            Message(role="user", content="Hello"),
            Message(role="assistant", content="Hi there"),
        ],
    )
    report = EvaluationReport(
        skill_name="my-skill",
        scenario_id="scenario-1",
        model_id="test-model",
        judge_model_id="judge-model",
        structural=[CriterionEval("s1", "desc", "pass", "ok")],
        qualitative=[CriterionEval("q1", "desc", "strong", "great")],
        anti_patterns=[CriterionEval("ap1", "desc", "clear", "fine")],
    )
    return trace, report


def test_save_trace(tmp_path: Path):
    trace, report = _make_trace_and_report()
    model = ModelConfig(id="test", model="test-model")
    judge = ModelConfig(id="judge", model="judge-model")

    path = save_trace(
        trace, report,
        group="test-group",
        version="1.0.0",
        scenario={"id": "scenario-1", "setup": "", "messages": []},
        model_config=model,
        judge_config=judge,
        traces_dir=tmp_path,
    )

    assert path.exists()
    assert path.name == "scenario-1_0001.json"
    assert path.parent == tmp_path / "test-group" / "my-skill" / "1.0.0"

    data = json.loads(path.read_text())
    assert data["meta"]["skill"] == "my-skill"
    assert data["meta"]["group"] == "test-group"
    assert data["meta"]["version"] == "1.0.0"
    assert data["evaluation"]["score"] > 0
    assert len(data["conversation"]) == 2


def test_save_trace_increments_sequence(tmp_path: Path):
    trace, report = _make_trace_and_report()
    model = ModelConfig(id="test", model="test-model")
    judge = ModelConfig(id="judge", model="judge-model")
    kwargs = dict(
        group="g", version="1.0.0",
        scenario={"id": "scenario-1", "messages": []},
        model_config=model, judge_config=judge,
        traces_dir=tmp_path,
    )

    p1 = save_trace(trace, report, **kwargs)
    p2 = save_trace(trace, report, **kwargs)

    assert p1.name == "scenario-1_0001.json"
    assert p2.name == "scenario-1_0002.json"


def test_trace_exists(tmp_path: Path):
    trace, report = _make_trace_and_report()
    model = ModelConfig(id="test", model="test-model")
    judge = ModelConfig(id="judge", model="judge-model")

    save_trace(
        trace, report,
        group="g", version="1.0.0",
        scenario={"id": "scenario-1", "messages": []},
        model_config=model, judge_config=judge,
        traces_dir=tmp_path,
    )

    assert trace_exists("my-skill", "1.0.0", "scenario-1", "test-model", traces_dir=tmp_path)
    assert not trace_exists("my-skill", "1.0.0", "scenario-1", "other-model", traces_dir=tmp_path)
    assert not trace_exists("other-skill", "1.0.0", "scenario-1", "test-model", traces_dir=tmp_path)


def test_rebuild_index(tmp_path: Path):
    trace, report = _make_trace_and_report()
    model = ModelConfig(id="test", model="test-model")
    judge = ModelConfig(id="judge", model="judge-model")

    save_trace(
        trace, report,
        group="g", version="1.0.0",
        scenario={"id": "s1", "messages": []},
        model_config=model, judge_config=judge,
        traces_dir=tmp_path,
    )
    save_trace(
        trace, report,
        group="g", version="1.0.0",
        scenario={"id": "s2", "messages": []},
        model_config=model, judge_config=judge,
        traces_dir=tmp_path,
    )

    count = rebuild_index(tmp_path)
    assert count == 2

    index_path = tmp_path / "index.json"
    assert index_path.exists()
    data = json.loads(index_path.read_text())
    assert len(data["traces"]) == 2
    # Each entry has expected fields
    entry = data["traces"][0]
    assert "path" in entry
    assert "skill" in entry
    assert "score" in entry
    assert "model" in entry


def test_rebuild_index_skips_malformed(tmp_path: Path):
    """Malformed JSON files are skipped, not crashing the index rebuild."""
    sub = tmp_path / "g" / "sk" / "1.0"
    sub.mkdir(parents=True)
    (sub / "bad_0001.json").write_text("not json", encoding="utf-8")
    (sub / "also_bad_0002.json").write_text('{"meta": {}}', encoding="utf-8")  # missing keys

    count = rebuild_index(tmp_path)
    assert count == 0

    index = json.loads((tmp_path / "index.json").read_text())
    assert index["traces"] == []
