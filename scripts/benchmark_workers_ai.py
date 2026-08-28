#!/usr/bin/env python3
"""
Workers AI Lesson Benchmark
===========================
Evaluate how Cloudflare Workers AI models handle real MisakaNet failure
scenarios. For each (model x scenario), ask the model for a fix and score
the response heuristically (commands present, actionability, length).

Usage:
    python3 scripts/benchmark_workers_ai.py [--models m1,m2] [--scenarios 3] [--output out.json]

Requires a valid Cloudflare OAuth token via mcporter (re-auth with:
    mcporter auth cloudflare --config .tools/mcporter.json --log-level info)
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ACCOUNT = "6b92325b505f2b76aec49e9fe4195d31"
MC = str(Path(__file__).resolve().parents[1] / ".tools" / "bin" / "mcporter")
CFG = str(Path(__file__).resolve().parents[1] / ".tools" / "mcporter.json")
REPO = Path(__file__).resolve().parents[1]

DEFAULT_MODELS = [
    "@cf/meta/llama-3.3-70b-instruct-fp8-fast",
    "@cf/qwen/qwen2.5-coder-32b-instruct",
    "@cf/meta/llama-3.2-3b-instruct",
]

# Fallback scenarios (used when lessons/ unavailable); normally read from lessons/
FALLBACK_SCENARIOS = [
    "DCO sign-off failed: git commit rejected with 'Missing Signed-off-by line'.",
    "pip install timeout / SSL CERTIFICATE_VERIFY_FAILED in China network.",
    "WSL permission denied when accessing files on the Windows drive.",
    "Database locked: SQLite 'database is locked' error during concurrent writes.",
]


def call_ai(model: str, prompt: str, timeout: int = 90) -> dict:
    """Call Workers AI via mcporter execute (Cloudflare-internal path)."""
    code = (
        "async () => { const res = await cloudflare.request({ method: 'POST', "
        f"path: '/accounts/{ACCOUNT}/ai/run/{model}', "
        f"body: {{ messages: [{{ role: 'user', content: {json.dumps(prompt)} }}] }} }}); "
        "const r = res.result || {}; "
        "const c = (r.choices && r.choices[0] && r.choices[0].message) "
        "? r.choices[0].message.content : (r.response || null); "
        "return { success: res.success, status: res.status, content: c, "
        "errors: res.errors }; }"
    )
    r = subprocess.run(
        [MC, "call", "cloudflare.execute", "code=" + code, "--config", CFG],
        capture_output=True, text=True, timeout=timeout,
    )
    try:
        return json.loads(r.stdout.strip())
    except json.JSONDecodeError:
        return {"success": False, "error": r.stdout[-300:]}


def load_scenarios(limit: int) -> list[str]:
    """Read representative failure scenarios from lessons/."""
    lessons_dir = REPO / "lessons"
    problems = []
    for sub in ("core", "contrib"):
        d = lessons_dir / sub
        if not d.is_dir():
            continue
        for md in sorted(d.glob("*.md")):
            if md.name in ("README.md", "index.md", "TEMPLATE.md"):
                continue
            text = md.read_text(encoding="utf-8", errors="ignore")
            fm = re.search(r"^---\n(.*?)\n---", text, re.S)
            title = ""
            if fm:
                t = re.search(r"title:\s*(.+)", fm.group(1))
                if t:
                    title = t.group(1).strip().strip("'\"")
            problem_match = re.search(r"## (?:Problem|问题)\s*\n(.*?)(?:\n##|\Z)", text, re.S)
            problem = problem_match.group(1).strip() if problem_match else ""
            scene = title or problem
            if scene and len(scene) > 20:
                problems.append(f"{scene} ({md.stem})")
    # dedupe, prefer core first then diverse contrib
    seen, chosen = set(), []
    for p in problems:
        key = p[:40]
        if key not in seen:
            seen.add(key)
            chosen.append(p)
    return chosen[:limit]


def score_response(content: str) -> dict:
    """Heuristic quality scoring of a model response."""
    if not content:
        return {"length": 0, "commands": 0, "has_command_block": False,
                "actionable": False, "has_code_inline": False}
    code_blocks = re.findall(r"```(?:bash|sh|shell|zsh)?\s*\n(.*?)```", content, re.S)
    commands = []
    for b in code_blocks:
        commands += [l.strip() for l in b.splitlines() if l.strip() and not l.strip().startswith("#")]
    inline_code = re.findall(r"`([^`]{3,})`", content)
    action_words = re.findall(r"\b(run|execute|install|configure|set|fix|use|try)\b", content, re.I)
    return {
        "length": len(content),
        "commands": len(commands),
        "command_list": commands[:5],
        "has_command_block": bool(code_blocks),
        "actionable": len(action_words) >= 2,
        "inline_code_count": len(inline_code),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Workers AI lesson benchmark")
    ap.add_argument("--models", help="comma-separated model ids")
    ap.add_argument("--scenarios", type=int, default=4, help="number of scenarios (from lessons/)")
    ap.add_argument("--output", help="JSON output path")
    args = ap.parse_args()

    models = args.models.split(",") if args.models else DEFAULT_MODELS
    scenarios = load_scenarios(args.scenarios) or FALLBACK_SCENARIOS
    if len(scenarios) < args.scenarios:
        scenarios += FALLBACK_SCENARIOS[: args.scenarios - len(scenarios)]

    print(f"Models ({len(models)}): {models}")
    print(f"Scenarios ({len(scenarios)}):")
    for i, s in enumerate(scenarios):
        print(f"  [{i}] {s[:70]}")

    results = {"models": models, "scenarios": scenarios, "runs": []}
    for model in models:
        for i, scene in enumerate(scenarios):
            short_name = model.rsplit("/", 1)[-1]
            prompt = f"I hit this error and need a fix:\n{scene}\n\nGive a concrete, actionable fix with exact commands."
            print(f"\n▶ {short_name} × scenario[{i}] ...", flush=True)
            resp = call_ai(model, prompt)
            content = resp.get("content") or ""
            metrics = score_response(content)
            print(f"  status={resp.get('status')} len={metrics['length']} "
                  f"cmds={metrics['commands']} actionable={metrics['actionable']}")
            results["runs"].append({
                "model": model,
                "scenario": scene,
                "status": resp.get("status"),
                "content": content,
                "metrics": metrics,
                "error": resp.get("errors") or resp.get("error"),
            })

    # summary table
    print("\n" + "=" * 72)
    print(f"{'MODEL':<40} {'SCEN':<4} {'LEN':<6} {'CMDS':<5} {'ACT':<5} STATUS")
    print("-" * 72)
    for run in results["runs"]:
        m = run["metrics"]
        name = run["model"].rsplit("/", 1)[-1]
        print(f"{name:<40} {run['scenario'][:4]:<4} {m['length']:<6} "
              f"{m['commands']:<5} {str(m['actionable']):<5} {run.get('status')}")
    print("=" * 72)

    if args.output:
        Path(args.output).write_text(json.dumps(results, ensure_ascii=False, indent=2))
        print(f"Saved: {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
