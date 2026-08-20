"""Skill evaluation tests — generic test module.

Projects can copy this into their tests/ directory, or just depend on it
directly since the conftest_plugin handles all the parametrization.

Run with:
    uv run pytest tests/ -v -s          # skip scenarios that already have traces
    uv run pytest tests/ -v -s --rerun  # force re-run everything
"""

from __future__ import annotations

import pytest

from skill_eval.evaluator import AntiPatternResult, evaluate_trace
from skill_eval.runner import ModelConfig, run_scenario
from skill_eval.trace_writer import save_trace, trace_exists

MINIMUM_SCORE = 50
NULL_VERSION = "_null"


def _skip_if_exists(request, skill: str, version: str, scenario_id: str, model: str, traces_dir):
    """Skip this test if a trace already exists, unless --rerun was passed."""
    if request.config.getoption("--rerun"):
        return
    if trace_exists(skill, version, scenario_id, model, traces_dir=traces_dir):
        pytest.skip(f"Trace exists for {skill}/{version}/{scenario_id} ({model}) — use --rerun to force")


def _run_and_evaluate(
    *,
    openai_client,
    model: ModelConfig,
    judge_models: list[ModelConfig],
    rubric: dict,
    scenario: dict,
    system_prompt: str,
    skill_name: str,
    group: str,
    version: str,
    traces_dir,
    minimum_score: int = MINIMUM_SCORE,
):
    """Run a scenario, evaluate it, save the trace, and assert quality."""
    trace = run_scenario(
        client=openai_client,
        model_config=model,
        system_prompt=system_prompt,
        scenario=scenario,
        skill_name=skill_name,
    )

    assert len(trace.agent_turns()) > 0, "Model produced no responses"

    for judge in judge_models:
        report = evaluate_trace(
            client=openai_client,
            judge=judge,
            rubric=rubric,
            trace=trace,
        )

        print(f"\n{report.summary()}\n")

        save_trace(
            trace,
            report,
            group=group,
            version=version,
            scenario=scenario,
            model_config=model,
            judge_config=judge,
            traces_dir=traces_dir,
        )

        assert not report.has_anti_pattern_violations(), (
            f"Anti-pattern violations detected:\n"
            + "\n".join(
                f"  {c.criterion_id}: {c.justification}"
                for c in report.anti_patterns
                if c.result == AntiPatternResult.VIOLATION.value
            )
        )

        score = report.score()
        assert score >= minimum_score, (
            f"Score {score:.0f} below minimum {minimum_score}\n{report.summary()}"
        )


@pytest.mark.parametrize("model_idx", [0], indirect=False)
def test_skill_scenario(
    request,
    rubric_scenario: dict,
    openai_client,
    models_under_test: list[ModelConfig],
    judge_models: list[ModelConfig],
    traces_dir,
    model_idx: int,
):
    """Run a skill scenario and evaluate the conversation against the rubric."""
    if model_idx >= len(models_under_test):
        pytest.skip(f"Model index {model_idx} out of range")

    model = models_under_test[model_idx]
    skill_name = rubric_scenario["skill_name"]
    version = rubric_scenario["version"]
    scenario = rubric_scenario["scenario"]

    _skip_if_exists(request, skill_name, version, scenario["id"], model.model, traces_dir)

    _run_and_evaluate(
        openai_client=openai_client,
        model=model,
        judge_models=judge_models,
        rubric=rubric_scenario["rubric"],
        scenario=scenario,
        system_prompt=rubric_scenario["system_prompt"],
        skill_name=skill_name,
        group=rubric_scenario["group"],
        version=version,
        traces_dir=traces_dir,
    )


@pytest.mark.parametrize("model_idx", [0], indirect=False)
def test_null_scenario(
    request,
    rubric_scenario: dict,
    openai_client,
    models_under_test: list[ModelConfig],
    judge_models: list[ModelConfig],
    traces_dir,
    model_idx: int,
):
    """Run the same scenario with NO skill — a bare-model baseline.

    Null baselines measure whether the skill is actually adding value.
    They use version '_null' and are not expected to pass the quality bar
    (minimum_score=0 so they always record but never fail the suite).
    """
    if model_idx >= len(models_under_test):
        pytest.skip(f"Model index {model_idx} out of range")

    model = models_under_test[model_idx]
    skill_name = rubric_scenario["skill_name"]
    scenario = rubric_scenario["scenario"]

    _skip_if_exists(request, skill_name, NULL_VERSION, scenario["id"], model.model, traces_dir)

    _run_and_evaluate(
        openai_client=openai_client,
        model=model,
        judge_models=judge_models,
        rubric=rubric_scenario["rubric"],
        scenario=scenario,
        system_prompt="You are a helpful assistant.",
        skill_name=skill_name,
        group=rubric_scenario["group"],
        version=NULL_VERSION,
        traces_dir=traces_dir,
        minimum_score=0,
    )
