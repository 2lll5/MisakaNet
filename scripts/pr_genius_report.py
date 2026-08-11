#!/usr/bin/env python3
"""Build an actionable PR Genius report from GitHub pull-request metadata."""

from __future__ import annotations

import argparse
import json
import os
import re
import urllib.request
from pathlib import PurePosixPath
from typing import Any

CODE_SUFFIXES = {
    ".c", ".cc", ".cpp", ".cs", ".go", ".java", ".js", ".jsx", ".kt",
    ".php", ".py", ".rb", ".rs", ".sh", ".swift", ".ts", ".tsx",
}
TEST_PARTS = {"test", "tests", "spec", "specs", "__tests__"}
ISSUE_REFERENCE = re.compile(
    r"(?i)(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s+(?:[\w.-]+/[\w.-]+)?#\d+|(?<!\w)#\d+"
)


def is_test(path: str) -> bool:
    parsed = PurePosixPath(path)
    name = parsed.name.lower()
    return bool(
        TEST_PARTS.intersection(part.lower() for part in parsed.parts)
        or name.startswith("test_")
        or ".test." in name
        or ".spec." in name
    )


def is_documentation(path: str) -> bool:
    parsed = PurePosixPath(path)
    return parsed.suffix.lower() in {".md", ".mdx", ".rst"} or bool(
        parsed.parts and parsed.parts[0].lower() in {"doc", "docs"}
    )


def is_code(path: str) -> bool:
    return PurePosixPath(path).suffix.lower() in CODE_SUFFIXES and not is_test(path)


def size_label(total: int) -> str:
    if total <= 100:
        return "small"
    if total <= 500:
        return "medium"
    return "large"


def component(path: str) -> str:
    parts = PurePosixPath(path).parts
    return parts[0] if len(parts) > 1 else "repository root"


def analyze(
    pr: dict[str, Any],
    files: list[dict[str, Any]],
    commits: list[dict[str, Any]],
    checks: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    additions = sum(int(item.get("additions", 0)) for item in files)
    deletions = sum(int(item.get("deletions", 0)) for item in files)
    total = additions + deletions
    paths = [str(item.get("filename", "")) for item in files]
    code_paths = [path for path in paths if is_code(path)]
    test_paths = [path for path in paths if is_test(path)]
    doc_paths = [path for path in paths if is_documentation(path)]
    components = sorted({component(path) for path in paths})

    patterns: list[dict[str, str]] = []
    suggestions: list[str] = []

    if total > 500:
        patterns.append({"rule": "pr_too_large", "severity": "high"})
        suggestions.append("Split the change into focused PRs of at most 500 changed lines.")
    if code_paths and not test_paths:
        patterns.append({"rule": "missing_tests", "severity": "medium"})
        suggestions.append("Add or update tests for the changed code paths.")
    if doc_paths and not code_paths and not test_paths:
        patterns.append({"rule": "doc_code_mismatch", "severity": "low"})
        suggestions.append(
            "Confirm this documentation-only change intentionally needs no code update."
        )

    concern_groups = set()
    if code_paths:
        concern_groups.add("code")
    if test_paths:
        concern_groups.add("tests")
    if doc_paths:
        concern_groups.add("docs")
    if any(path.startswith(".github/") for path in paths):
        concern_groups.add("automation")
    lock_files = {"package-lock.json", "uv.lock", "poetry.lock"}
    if any(PurePosixPath(path).name.lower() in lock_files for path in paths):
        concern_groups.add("dependencies")
    if len(concern_groups) >= 3 and len(components) >= 3:
        patterns.append({"rule": "mixed_concerns", "severity": "medium"})
        suggestions.append(
            "Explain why these components belong together or split unrelated concerns."
        )

    body = str(pr.get("body") or "")
    if not ISSUE_REFERENCE.search(body):
        patterns.append({"rule": "no_issue_reference", "severity": "low"})
        suggestions.append("Link the issue this PR closes or explain why no issue is needed.")

    unsigned = []
    for item in commits:
        commit = item.get("commit") or {}
        message = str(commit.get("message") or "")
        if not re.search(r"(?im)^Signed-off-by:\s*.+<[^>]+>\s*$", message):
            unsigned.append(str(item.get("sha", "unknown"))[:7])
    if unsigned:
        patterns.append({"rule": "missing_dco", "severity": "medium"})
        suggestions.append("Sign off every commit with `git commit --signoff`.")

    relevant_checks = [
        check for check in (checks or []) if "pr genius" not in str(check.get("name", "")).lower()
    ]
    failed_conclusions = {
        "action_required",
        "cancelled",
        "failure",
        "startup_failure",
        "timed_out",
    }
    if any(check.get("conclusion") in failed_conclusions for check in relevant_checks):
        ci_status, ci_detail = "FAIL", "one or more checks failed"
    elif any(check.get("status") != "completed" for check in relevant_checks):
        ci_status, ci_detail = "PENDING", "checks are still running"
    elif relevant_checks:
        ci_status, ci_detail = "PASS", f"{len(relevant_checks)} check(s) completed"
    else:
        ci_status, ci_detail = "UNKNOWN", "no completed CI checks found"

    checklist = [
        {"name": "ci_passing", "status": ci_status, "detail": ci_detail},
        {
            "name": "dco_signoff",
            "status": "FAIL" if unsigned else "PASS",
            "detail": f"{len(unsigned)} unsigned commit(s)" if unsigned else "all commits signed",
        },
        {
            "name": "tests_updated",
            "status": "PASS" if test_paths or not code_paths else "FAIL",
            "detail": f"{len(test_paths)} test file(s) changed",
        },
        {
            "name": "issue_reference",
            "status": "PASS" if ISSUE_REFERENCE.search(body) else "FAIL",
            "detail": (
                "linked issue found" if ISSUE_REFERENCE.search(body) else "no linked issue found"
            ),
        },
    ]

    if not suggestions:
        suggestions.append("No structural changes suggested; proceed with normal review.")

    return {
        "size": {
            "additions": additions,
            "deletions": deletions,
            "total": total,
            "label": size_label(total),
        },
        "impact": {"files_changed": len(paths), "components": components},
        "checklist": checklist,
        "anti_patterns": patterns,
        "suggestions": suggestions,
    }


def render(report: dict[str, Any], risk: str) -> str:
    size = report["size"]
    impact = report["impact"]
    components = ", ".join(impact["components"]) or "none"
    lines = [
        "## PR Genius Analysis",
        f"- **Risk Level:** {risk or 'unknown'}",
        (
            f"- **PR Size:** +{size['additions']}/-{size['deletions']} "
            f"({size['total']} lines, {size['label']})"
        ),
        f"- **Impact:** {impact['files_changed']} files changed ({components})",
        "",
        "### Checklist",
    ]
    for item in report["checklist"]:
        lines.append(f"- **{item['name']} ({item['status']})** — {item['detail']}")
    lines.extend(["", "### Anti-Patterns Detected"])
    if report["anti_patterns"]:
        for item in report["anti_patterns"]:
            lines.append(f"- **{item['rule']}** ({item['severity']})")
    else:
        lines.append("- None detected")
    lines.extend(["", "### Suggestions"])
    lines.extend(f"- {suggestion}" for suggestion in report["suggestions"])
    return "\n".join(lines)


def github_get(url: str, token: str) -> Any:
    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def github_get_all(url: str, token: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    page = 1
    separator = "&" if "?" in url else "?"
    while True:
        batch = github_get(f"{url}{separator}per_page=100&page={page}", token)
        items.extend(batch)
        if len(batch) < 100:
            return items
        page += 1


def github_get_check_runs(url: str, token: str) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    page = 1
    while True:
        response = github_get(f"{url}?per_page=100&page={page}", token)
        batch = response.get("check_runs", [])
        checks.extend(batch)
        if len(batch) < 100:
            return checks
        page += 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--event", required=True, help="GitHub pull_request event JSON")
    parser.add_argument("--risk", default="unknown")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of Markdown")
    args = parser.parse_args()

    with open(args.event, encoding="utf-8") as handle:
        event = json.load(handle)
    pr = event["pull_request"]
    repository = event["repository"]["full_name"]
    number = pr["number"]
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        raise SystemExit("GITHUB_TOKEN is required")
    base = f"https://api.github.com/repos/{repository}/pulls/{number}"
    files = github_get_all(f"{base}/files", token)
    commits = github_get_all(f"{base}/commits", token)
    checks_url = (
        f"https://api.github.com/repos/{repository}/commits/{pr['head']['sha']}/check-runs"
    )
    checks = github_get_check_runs(checks_url, token)
    report = analyze(pr, files, commits, checks)
    output = json.dumps(report, indent=2) if args.json else render(report, args.risk)
    print(output)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary and not args.json:
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write(output + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
