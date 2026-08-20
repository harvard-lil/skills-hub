"""Skill evaluation tests for the Data Monitoring Toolkit.

This file re-exports the generic test module from skill-eval.
The conftest_plugin handles all discovery and parametrization automatically.

Run with:
    uv run pytest tests/ -v -s
    uv run pytest tests/ -v -s --rerun   # force re-run
"""

from skill_eval.test_skills import *  # noqa: F401, F403
