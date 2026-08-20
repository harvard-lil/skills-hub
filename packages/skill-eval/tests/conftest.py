"""Shared fixtures for skill-eval tests."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from skill_eval.runner import ConversationTrace, Message, ModelConfig


@pytest.fixture
def sample_trace() -> ConversationTrace:
    return ConversationTrace(
        skill_name="test-skill",
        scenario_id="happy-path",
        model_id="test-model",
        messages=[
            Message(role="user", content="Help me with X"),
            Message(role="assistant", content="Sure, let me ask: what kind of X?"),
            Message(role="user", content="The data kind"),
            Message(role="assistant", content="Here's my analysis of your data..."),
        ],
    )


@pytest.fixture
def sample_rubric() -> dict:
    return {
        "group": "test-group",
        "skill": "test-skill",
        "criteria": {
            "structural": [
                {
                    "id": "asks-questions",
                    "description": "Agent asks clarifying questions",
                    "check": "Agent asks at least one question before giving final answer",
                },
                {
                    "id": "provides-analysis",
                    "description": "Agent provides substantive analysis",
                    "check": "Agent response contains analytical content",
                },
            ],
            "qualitative": [
                {
                    "id": "clear-communication",
                    "description": "Agent communicates clearly",
                    "weight": "high",
                },
            ],
        },
        "anti_patterns": [
            {
                "id": "fabricates-data",
                "description": "Agent invents information",
                "check": "Agent makes claims without evidence",
            },
        ],
        "test_scenarios": [
            {
                "id": "happy-path",
                "setup": "User needs help with data",
                "messages": [
                    {"role": "user", "content": "Help me with X"},
                    {"role": "user", "content": "The data kind"},
                ],
                "expected": ["Agent asks questions", "Agent provides analysis"],
            },
        ],
    }


@pytest.fixture
def model_config() -> ModelConfig:
    return ModelConfig(id="test", model="test-model", temperature=0.0, max_tokens=100)


@pytest.fixture
def judge_config() -> ModelConfig:
    return ModelConfig(id="judge", model="judge-model", temperature=0.0, max_tokens=100)


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client that returns predictable responses."""
    client = MagicMock()

    def make_response(content: str):
        resp = MagicMock()
        resp.choices = [MagicMock()]
        resp.choices[0].message.content = content
        resp.usage = MagicMock()
        resp.usage.prompt_tokens = 100
        resp.usage.completion_tokens = 50
        return resp

    # Default: returns a simple assistant response
    client.chat.completions.create.return_value = make_response(
        "I'd be happy to help. What specifically do you need?"
    )

    client._make_response = make_response
    return client
