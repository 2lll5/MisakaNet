import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bench" / "phase-b" / "orchestrator.py"


def _module():
    spec = importlib.util.spec_from_file_location("phase_b_orchestrator", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_catalog_has_three_failure_fixtures():
    module = _module()
    tasks = module.load_tasks()
    assert {task["task_id"] for task in tasks} == {"dco-signoff", "pytest-import", "mcp-crash"}


def test_run_is_sequential_and_records_outcomes():
    module = _module()
    result = module.run(module.load_tasks(), timeout=5, seed=42)
    assert result["meta"]["seed"] == 42
    assert result["summary"]["total_tasks"] == 3
    assert all(row["attempts"] == 1 for row in result["tasks"])
    assert {row["outcome"] for row in result["tasks"]} == {"failure"}
    assert all(row["duration_ms"] >= 0 for row in result["tasks"])


def test_dry_run_output_contract_is_json(tmp_path):
    module = _module()
    output = tmp_path / "results.json"
    result = module.run(module.load_tasks(), timeout=5)
    output.write_text(json.dumps(result), encoding="utf-8")
    loaded = json.loads(output.read_text(encoding="utf-8"))
    assert loaded["summary"]["total_tasks"] == 3
