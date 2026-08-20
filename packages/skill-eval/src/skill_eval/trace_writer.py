"""Write conversation traces and evaluation reports to disk.

Traces are saved as JSON files:
    traces/<group>/<skill-name>/<version>/<scenario-id>_<sequence>.json

The sequence number auto-increments so multiple runs accumulate over time,
enabling quality trending.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .evaluator import EvaluationReport
from .runner import ConversationTrace, ModelConfig

log = logging.getLogger("skill_eval.traces")


def _next_sequence(directory: Path, prefix: str) -> int:
    """Find the next available sequence number for a given scenario prefix."""
    existing = sorted(directory.glob(f"{prefix}_*.json"))
    if not existing:
        return 1
    last = existing[-1].stem
    try:
        return int(last.rsplit("_", 1)[1]) + 1
    except (IndexError, ValueError):
        return len(existing) + 1


def save_trace(
    trace: ConversationTrace,
    report: EvaluationReport,
    *,
    group: str,
    version: str,
    scenario: dict,
    model_config: ModelConfig,
    judge_config: ModelConfig,
    traces_dir: Path,
) -> Path:
    """Serialize a trace + evaluation to JSON and write it to traces/.

    Returns the path to the written file.
    """
    out_dir = traces_dir / group / trace.skill_name / version
    out_dir.mkdir(parents=True, exist_ok=True)

    seq = _next_sequence(out_dir, trace.scenario_id)
    filename = f"{trace.scenario_id}_{seq:04d}.json"
    out_path = out_dir / filename

    record = {
        "meta": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "group": group,
            "skill": trace.skill_name,
            "version": version,
            "scenario_id": trace.scenario_id,
        },
        "config": {
            "model_under_test": asdict(model_config),
            "judge_model": asdict(judge_config),
        },
        "scenario": {
            "id": scenario["id"],
            "setup": scenario.get("setup", ""),
            "messages": scenario.get("messages", []),
            "expected": scenario.get("expected", []),
        },
        "conversation": [
            {"role": m.role, "content": m.content}
            for m in trace.messages
        ],
        "evaluation": {
            "score": round(report.score(), 1),
            "structural": [asdict(c) for c in report.structural],
            "qualitative": [asdict(c) for c in report.qualitative],
            "anti_patterns": [asdict(c) for c in report.anti_patterns],
        },
    }

    out_path.write_text(
        json.dumps(record, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    log.info("Trace saved: %s", out_path)
    return out_path


def trace_exists(
    skill: str, version: str, scenario_id: str, model: str, *, traces_dir: Path
) -> bool:
    """Check whether a trace already exists for this combination."""
    for trace_file in traces_dir.glob(f"*/{skill}/{version}/{scenario_id}_*.json"):
        try:
            record = json.loads(trace_file.read_text(encoding="utf-8"))
            if record["config"]["model_under_test"]["model"] == model:
                return True
        except (json.JSONDecodeError, KeyError, OSError):
            continue
    return False


def rebuild_index(traces_dir: Path) -> int:
    """Rebuild traces/index.json from all trace files on disk.

    Returns the number of traces indexed.
    """
    entries = []
    for trace_file in sorted(traces_dir.rglob("*.json")):
        if trace_file.name == "index.json":
            continue
        try:
            record = json.loads(trace_file.read_text(encoding="utf-8"))
            meta = record["meta"]
            config = record["config"]
            rel_path = trace_file.relative_to(traces_dir)
            entries.append({
                "path": str(rel_path),
                "group": meta["group"],
                "skill": meta["skill"],
                "version": meta["version"],
                "scenario_id": meta["scenario_id"],
                "timestamp": meta["timestamp"],
                "score": record["evaluation"]["score"],
                "model": config["model_under_test"]["model"],
                "judge": config["judge_model"]["model"],
            })
        except (json.JSONDecodeError, KeyError) as exc:
            log.warning("Skipping malformed trace %s: %s", trace_file, exc)

    entries.sort(key=lambda e: e["timestamp"])
    index_path = traces_dir / "index.json"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(
        json.dumps({"traces": entries}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    log.info("Rebuilt trace index: %d traces", len(entries))
    return len(entries)
