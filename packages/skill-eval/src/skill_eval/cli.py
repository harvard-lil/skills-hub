"""CLI entry point for skill-eval."""

from __future__ import annotations

from pathlib import Path

import click


@click.group()
def main():
    """skill-eval — evaluate AI agent skills against rubrics."""
    pass


@main.command()
@click.option(
    "--project", "-p",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=".",
    help="Project root directory (containing skills/ and eval.yaml).",
)
@click.option(
    "--rerun", is_flag=True, default=False,
    help="Re-run scenarios even if traces already exist.",
)
@click.option(
    "--verbose", "-v", is_flag=True, default=False,
    help="Verbose output.",
)
def run(project: Path, rerun: bool, verbose: bool):
    """Run skill evaluations (delegates to pytest)."""
    import subprocess
    import sys

    cmd = [sys.executable, "-m", "pytest", str(project / "tests"), "-v", "-s"]
    if rerun:
        cmd.append("--rerun")
    if verbose:
        cmd.append("-vv")

    result = subprocess.run(cmd, cwd=str(project))
    raise SystemExit(result.returncode)


@main.command()
@click.option(
    "--project", "-p",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=".",
    help="Project root directory.",
)
def index(project: Path):
    """Rebuild the trace index from existing trace files."""
    from .trace_writer import rebuild_index

    traces_dir = project / "traces"
    if not traces_dir.is_dir():
        click.echo("No traces/ directory found.")
        return

    count = rebuild_index(traces_dir)
    click.echo(f"Indexed {count} traces.")


@main.command()
@click.option(
    "--project", "-p",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=".",
    help="Project root directory.",
)
def discover(project: Path):
    """Show discovered rubrics and scenarios."""
    from .conftest_plugin import discover_rubrics

    skills_dir = project / "skills"
    if not skills_dir.is_dir():
        click.echo("No skills/ directory found.")
        return

    rubrics = discover_rubrics(skills_dir)
    if not rubrics:
        click.echo("No rubric.yaml files found.")
        return

    for rubric in rubrics:
        skill = rubric.get("skill", "unknown")
        group = rubric["_group"]
        scenarios = rubric.get("test_scenarios", [])
        click.echo(f"\n{group}/{skill} (v{rubric['_version']})")
        click.echo(f"  Structural criteria: {len(rubric.get('criteria', {}).get('structural', []))}")
        click.echo(f"  Qualitative criteria: {len(rubric.get('criteria', {}).get('qualitative', rubric.get('criteria', {}).get('pedagogical', [])))}")
        click.echo(f"  Anti-patterns: {len(rubric.get('anti_patterns', []))}")
        click.echo(f"  Scenarios: {len(scenarios)}")
        for s in scenarios:
            click.echo(f"    - {s['id']}")
