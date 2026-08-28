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
    """Call Workers AI. Uses CLOUDFLARE_API_TOKEN directly when set (CI),
    otherwise via mcporter execute (Cloudflare-internal path)."""
    import os as _os
    token = _os.environ.get("CLOUDFLARE_API_TOKEN")
    if token:
        import urllib.request as _ur
        req = _ur.Request(
            f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT}/ai/run/{model}",
            data=json.dumps({"messages": [{"role": "user", "content": prompt}]}).encode(),
            headers={"Authorization": f"Bearer {token}",
                     "Content-Type": "application/json",
                     "User-Agent": "misakanet-benchmark"},
            method="POST",
        )
        try:
            with _ur.urlopen(req, timeout=timeout) as r:
                d = json.loads(r.read())
            r_ = d.get("result") or {}
            c = (r_.get("choices") and r_.get("choices")[0].get("message", {}).get("content")) or r_.get("response")
            return {"success": d.get("success"), "status": d.get("status") or 200,
                    "content": c, "errors": d.get("errors")}
        except Exception as e:
            return {"success": False, "error": str(e)[:300]}
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


def load_lesson_context(scene: str, max_chars: int = 1500) -> tuple:
    """Load lesson content + fix commands for a scenario (matched by trailing stem).
    Returns (context_text, fix_commands)."""
    stem = scene.rsplit("(", 1)[-1].rstrip(")") if scene.endswith(")") else ""
    if stem:
        for sub in ("core", "contrib"):
            p = REPO / "lessons" / sub / f"{stem}.md"
            if p.exists():
                text = p.read_text(encoding="utf-8", errors="ignore")
                body = re.sub(r"^---\n.*?\n---", "", text, flags=re.S)
                # fix commands = code blocks from the Fix/修复 section
                fix_sec = re.search(r"## (?:Solution|Fix|修复|解法)\s*\n(.*?)(?:\n##|\Z)", text, re.S)
                cmds = []
                if fix_sec:
                    cmds = [l.strip() for l in re.findall(r"`([^`]{6,})`", fix_sec.group(1))]
                    cmds += [l.strip() for l in re.findall(r"```\w*\s*\n(.*?)```", fix_sec.group(1), re.S)
                             for l in l.splitlines() if l.strip() and not l.strip().startswith("#")]
                clean = re.sub(r"[#*`>]", "", body)
                return clean.strip()[:max_chars], list(dict.fromkeys(cmds))[:6]
    return "", []


def _lesson_has_commands(md: Path) -> bool:
    """A lesson is command-bearing if its Solution/Fix section contains inline code or a code block."""
    text = md.read_text(encoding="utf-8", errors="ignore")
    fix_sec = re.search(r"## (?:Solution|Fix|修复|解法)\s*\n(.*?)(?:\n##|\Z)", text, re.S)
    if not fix_sec:
        return False
    return bool(re.search(r"`[^`]{6,}`|```", fix_sec.group(1)))


def load_scenarios(limit: int) -> list[str]:
    """Read representative failure scenarios from lessons/, preferring
    command-bearing (concrete, fixable) lessons so the compare metric is meaningful."""
    lessons_dir = REPO / "lessons"
    with_cmds, without_cmds = [], []
    for sub in ("core", "contrib"):
        d = lessons_dir / sub
        if not d.is_dir():
            continue
        for md in sorted(d.glob("*.md")):
            if md.name in ("README.md", "index.md", "TEMPLATE.md"):
                continue
            text = md.read_text(encoding="utf-8", errors="ignore")
            title = ""
            fm = re.search(r"^---\n(.*?)\n---", text, re.S)
            if fm:
                t = re.search(r"title:\s*(.+)", fm.group(1))
                if t:
                    title = t.group(1).strip().strip("'\"")
            problem_match = re.search(r"## (?:Problem|问题)\s*\n(.*?)(?:\n##|\Z)", text, re.S)
            problem = problem_match.group(1).strip() if problem_match else ""
            scene = (title or problem)
            if scene and len(scene) > 20:
                entry = f"{scene} ({md.stem})"
                (with_cmds if _lesson_has_commands(md) else without_cmds).append(entry)
    chosen = (with_cmds + without_cmds)[:limit]
    return chosen


def score_response(content: str, reference_commands: list | None = None) -> dict:
    """Heuristic quality scoring of a model response.
    reference_commands: lesson fix commands — hit-rate shows whether the model
    adopted lesson-specific knowledge (distinctiveness of this repo's lessons)."""
    if not content:
        return {"length": 0, "commands": 0, "has_command_block": False,
                "actionable": False, "has_code_inline": False, "lesson_hits": 0, "lesson_hit_rate": 0.0}
    code_blocks = re.findall(r"```(?:bash|sh|shell|zsh)?\s*\n(.*?)```", content, re.S)
    commands = []
    for b in code_blocks:
        commands += [l.strip() for l in b.splitlines() if l.strip() and not l.strip().startswith("#")]
    inline_code = re.findall(r"`([^`]{3,})`", content)
    action_words = re.findall(r"\b(run|execute|install|configure|set|fix|use|try)\b", content, re.I)
    hits = 0
    if reference_commands:
        norm = content.lower()
        for rc in reference_commands:
            key = rc.lower()
            if key in norm or any(k in norm for k in key.split() if len(k) > 4):
                hits += 1
    rate = (hits / len(reference_commands)) if reference_commands else 0.0
    return {
        "length": len(content),
        "commands": len(commands),
        "command_list": commands[:5],
        "has_command_block": bool(code_blocks),
        "actionable": len(action_words) >= 2,
        "inline_code_count": len(inline_code),
        "lesson_hits": hits,
        "lesson_hit_rate": round(rate, 3),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Workers AI lesson benchmark")
    ap.add_argument("--models", help="comma-separated model ids")
    ap.add_argument("--scenarios", type=int, default=4, help="number of scenarios (from lessons/)")
    ap.add_argument("--output", help="JSON output path")
    ap.add_argument("--compare", action="store_true",
                    help="compare: same scenario with vs without lesson context (RAG ablation)")
    args = ap.parse_args()

    models = args.models.split(",") if args.models else DEFAULT_MODELS
    compare = args.compare
    scenarios = load_scenarios(args.scenarios) or FALLBACK_SCENARIOS
    if len(scenarios) < args.scenarios:
        scenarios += FALLBACK_SCENARIOS[: args.scenarios - len(scenarios)]

    print(f"Models ({len(models)}): {models}")
    print(f"Scenarios ({len(scenarios)}):")
    for i, s in enumerate(scenarios):
        print(f"  [{i}] {s[:70]}")

    results = {"models": models, "scenarios": scenarios, "compare": compare, "runs": []}
    for model in models:
        for i, scene in enumerate(scenarios):
            short_name = model.rsplit("/", 1)[-1]
            base_prompt = f"I hit this error and need a fix:\n{scene}\n\nGive a concrete, actionable fix with exact commands."
            print(f"\n▶ {short_name} × scenario[{i}] ...", flush=True)
            if compare:
                ctx, ref_cmds = load_lesson_context(scene)
                ctx_prompt = (f"I hit this error and need a fix:\n{scene}\n\n"
                              f"Here is a verified lesson about this failure:\n{ctx}\n\n"
                              f"Give a concrete, actionable fix with exact commands.")
                resp = call_ai(model, ctx_prompt)
                resp_plain = call_ai(model, base_prompt)
                for cond, r_ in (("with_lesson", resp), ("plain", resp_plain)):
                    content = r_.get("content") or ""
                    metrics = score_response(content, ref_cmds)
                    print(f"  [{cond}] status={r_.get('status')} len={metrics['length']} "
                          f"cmds={metrics['commands']} actionable={metrics['actionable']}")
                    results["runs"].append({
                        "model": model, "scenario": scene, "condition": cond,
                        "status": r_.get("status"), "content": content,
                        "metrics": metrics,
                        "error": r_.get("errors") or r_.get("error"),
                    })
            else:
                resp = call_ai(model, base_prompt)
                content = resp.get("content") or ""
                metrics = score_response(content)
                print(f"  status={resp.get('status')} len={metrics['length']} "
                      f"cmds={metrics['commands']} actionable={metrics['actionable']}")
                results["runs"].append({
                    "model": model, "scenario": scene,
                    "status": resp.get("status"), "content": content,
                    "metrics": metrics,
                    "error": resp.get("errors") or resp.get("error"),
                })

    # summary table
    print("\n" + "=" * 72)
    print(f"{'MODEL':<38} {'SCEN':<5} {'COND':<11} {'LEN':<6} {'CMDS':<5} {'HIT%':<6} STATUS")
    print("-" * 78)
    for run in results["runs"]:
        m = run["metrics"]
        name = run["model"].rsplit("/", 1)[-1]
        cond = run.get("condition", "-")
        hit = f"{int(m.get('lesson_hit_rate', 0) * 100)}%"
        print(f"{name:<38} {run['scenario'][:4]:<5} {cond:<11} {m['length']:<6} "
              f"{m['commands']:<5} {hit:<6} {run.get('status')}")
    print("=" * 78)

    if args.output:
        Path(args.output).write_text(json.dumps(results, ensure_ascii=False, indent=2))
        print(f"Saved: {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
