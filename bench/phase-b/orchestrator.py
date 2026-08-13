#!/usr/bin/env python3
"""Phase B benchmark orchestrator with isolated, timed task execution.

The runner deliberately does not invoke a paid model.  It executes the
checked-in fixtures (or an explicitly supplied agent command), records the
observed outcome, and leaves the model integration as a replaceable boundary.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import shlex
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TASKS = Path(__file__).with_name("tasks.json")
SANDBOX = Path(__file__).with_name("sandbox.sh")


def load_tasks(path: Path = DEFAULT_TASKS) -> list[dict]:
    """Load and validate the small, reviewable task catalog."""
    rows = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(rows, list) or not rows:
        raise ValueError("tasks.json must contain a non-empty array")
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or not row.get("task_id"):
            raise ValueError("each task requires a task_id")
        if row["task_id"] in seen:
            raise ValueError(f"duplicate task_id: {row['task_id']}")
        if not isinstance(row.get("fixture"), str) or not row["fixture"].strip():
            raise ValueError(f"task {row['task_id']} requires a fixture")
        seen.add(row["task_id"])
    return rows


def _run_command(command: list[str], cwd: Path, timeout: float) -> tuple[str, str, int | None, float]:
    started = time.monotonic()
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env={
                "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                "PYTHONDONTWRITEBYTECODE": "1",
            },
        )
        outcome = "success" if completed.returncode == 0 else "failure"
        output = (completed.stdout + completed.stderr).strip()
        return outcome, output, completed.returncode, time.monotonic() - started
    except subprocess.TimeoutExpired as exc:
        output = ((exc.stdout or "") + (exc.stderr or "")).strip()
        return "timeout", output or f"timed out after {timeout}s", None, time.monotonic() - started
    except OSError as exc:
        return "error", str(exc), None, time.monotonic() - started


def run_task(task: dict, timeout: float = 30, agent_command: str | None = None) -> dict:
    """Run a task in a fresh temp directory and return a result row."""
    with tempfile.TemporaryDirectory(prefix=f"misakanet-{task['task_id']}-") as temp:
        root = Path(temp)
        fixture = root / "fixture.py"
        fixture.write_text(task["fixture"], encoding="utf-8")
        if agent_command:
            command = shlex.split(agent_command) + [str(fixture)]
        else:
            command = ["bash", str(SANDBOX), str(fixture)]
        outcome, output, returncode, elapsed = _run_command(command, root, timeout)
    return {
        "task_id": task["task_id"],
        "name": task.get("name", task["task_id"]),
        "category": task.get("category", ""),
        "outcome": outcome,
        "attempts": 1,
        "duration_ms": round(elapsed * 1000, 3),
        "cost_usd": 0.0,
        "lessons_used": [],
        "error": None if outcome == "success" else output,
        "returncode": returncode,
    }


def run(tasks: list[dict], timeout: float = 30, seed: int | None = None,
        agent_command: str | None = None) -> dict:
    """Run tasks sequentially and produce a machine-readable report."""
    ordered = list(tasks)
    if seed is not None:
        random.Random(seed).shuffle(ordered)
    rows = [run_task(task, timeout=timeout, agent_command=agent_command) for task in ordered]
    successful = sum(row["outcome"] == "success" for row in rows)
    total = len(rows)
    return {
        "meta": {
            "run_id": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "git_sha": _git_sha(),
            "seed": seed,
            "timeout_seconds": timeout,
            "agent_command": agent_command or "fixture sandbox",
        },
        "tasks": rows,
        "summary": {
            "total_tasks": total,
            "success_rate": round(successful / total, 6) if total else 0.0,
            "mean_attempts": round(sum(row["attempts"] for row in rows) / total, 3) if total else 0.0,
            "mean_duration": round(sum(row["duration_ms"] for row in rows) / total, 3) if total else 0.0,
            "total_cost": 0.0,
        },
    }


def _git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, timeout=5).strip()
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tasks", type=Path, default=DEFAULT_TASKS)
    parser.add_argument("--output", type=Path, default=Path("bench_results/phase-b/results.json"))
    parser.add_argument("--timeout", type=float, default=30)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--agent-command", help="Optional command that receives the fixture path")
    parser.add_argument("--dry-run", action="store_true", help="List tasks without executing fixtures")
    args = parser.parse_args()
    tasks = load_tasks(args.tasks)
    if args.dry_run:
        print(json.dumps({"tasks": [task["task_id"] for task in tasks], "seed": args.seed}, indent=2))
        return 0
    result = run(tasks, timeout=args.timeout, seed=args.seed, agent_command=args.agent_command)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {args.output}")
    print(f"summary: {result['summary']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
