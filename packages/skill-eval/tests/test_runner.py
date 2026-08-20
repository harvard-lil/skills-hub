"""Tests for the conversation scenario runner."""

from pathlib import Path
from unittest.mock import MagicMock

from skill_eval.runner import (
    ConversationTrace,
    Message,
    ModelConfig,
    load_skill_as_system_prompt,
    run_scenario,
)


def test_conversation_trace_transcript(sample_trace):
    transcript = sample_trace.as_transcript()
    assert "[USER]" in transcript
    assert "[AGENT]" in transcript
    assert "Help me with X" in transcript
    assert "Here's my analysis" in transcript


def test_conversation_trace_turns(sample_trace):
    assert len(sample_trace.agent_turns()) == 2
    assert len(sample_trace.user_turns()) == 2


def test_load_skill_as_system_prompt(tmp_path: Path):
    skill_md = tmp_path / "SKILL.md"
    skill_md.write_text(
        "---\nname: test\ndescription: test skill\n---\n\n# Test\n\nDo things.\n",
        encoding="utf-8",
    )
    prompt = load_skill_as_system_prompt(skill_md)
    assert "You are an AI agent with the following skill installed" in prompt
    assert "# Test" in prompt
    assert "Do things." in prompt


def test_run_scenario(mock_openai_client, model_config):
    scenario = {
        "id": "test-scenario",
        "setup": "User is a researcher",
        "messages": [
            {"role": "user", "content": "Hello"},
            {"role": "user", "content": "Can you help?"},
        ],
    }

    trace = run_scenario(
        client=mock_openai_client,
        model_config=model_config,
        system_prompt="You are helpful.",
        scenario=scenario,
        skill_name="test-skill",
    )

    assert trace.skill_name == "test-skill"
    assert trace.scenario_id == "test-scenario"
    assert trace.model_id == "test"
    assert len(trace.user_turns()) == 2
    assert len(trace.agent_turns()) == 2
    # API was called twice (once per user message)
    assert mock_openai_client.chat.completions.create.call_count == 2


def test_run_scenario_sends_setup_as_system(mock_openai_client, model_config):
    scenario = {
        "id": "with-setup",
        "setup": "User is a librarian",
        "messages": [{"role": "user", "content": "Hi"}],
    }

    run_scenario(
        client=mock_openai_client,
        model_config=model_config,
        system_prompt="Be helpful.",
        scenario=scenario,
        skill_name="s",
    )

    call_args = mock_openai_client.chat.completions.create.call_args
    messages = call_args.kwargs["messages"]
    # Should have: system prompt, setup system message, user message
    system_msgs = [m for m in messages if m["role"] == "system"]
    assert len(system_msgs) == 2
    assert "librarian" in system_msgs[1]["content"]


def test_run_scenario_no_setup(mock_openai_client, model_config):
    scenario = {
        "id": "no-setup",
        "messages": [{"role": "user", "content": "Hi"}],
    }

    run_scenario(
        client=mock_openai_client,
        model_config=model_config,
        system_prompt="Be helpful.",
        scenario=scenario,
        skill_name="s",
    )

    call_args = mock_openai_client.chat.completions.create.call_args
    messages = call_args.kwargs["messages"]
    system_msgs = [m for m in messages if m["role"] == "system"]
    assert len(system_msgs) == 1  # Just the skill prompt
