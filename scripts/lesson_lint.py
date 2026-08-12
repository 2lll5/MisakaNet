#!/usr/bin/env python3
"""Lightweight lesson lint / health check.

Checks for:
- Broken links (relative links to non-existent files)
- Duplicate titles
- Missing frontmatter
- Quality score anomalies
- Empty or too-short lessons
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


def check_frontmatter(content: str, file_path: Path) -> list[dict[str, str]]:
    """Check for valid YAML/JSON frontmatter."""
    issues = []
    if not content.startswith("---") and not content.startswith("{"):
        issues.append({
            "rule": "missing_frontmatter",
            "severity": "high",
            "file": str(file_path),
            "message": "No frontmatter found (expected YAML --- or JSON {})"
        })
    return issues


def check_title(content: str, file_path: Path) -> list[dict[str, str]]:
    """Check for H1 title."""
    issues = []
    lines = content.split("\n")
    has_h1 = any(line.startswith("# ") for line in lines[:10])
    if not has_h1:
        issues.append({
            "rule": "missing_title",
            "severity": "medium",
            "file": str(file_path),
            "message": "No H1 title found in first 10 lines"
        })
    return issues


def check_length(content: str, file_path: Path) -> list[dict[str, str]]:
    """Check lesson length."""
    issues = []
    lines = content.split("\n")
    # Strip frontmatter
    body_start = 0
    if content.startswith("---"):
        for i, line in enumerate(lines[1:], 1):
            if line.strip() == "---":
                body_start = i + 1
                break
    body_lines = len(lines[body_start:])
    if body_lines < 10:
        issues.append({
            "rule": "too_short",
            "severity": "medium",
            "file": str(file_path),
            "message": f"Lesson body is only {body_lines} lines (minimum 10)"
        })
    return issues


def check_links(content: str, file_path: Path, lessons_dir: Path) -> list[dict[str, str]]:
    """Check for broken relative links."""
    issues = []
    # Find markdown links: [text](path)
    link_pattern = re.compile(r'\[([^\]]*)\]\(([^)]+)\)')
    for match in link_pattern.finditer(content):
        link_text, link_path = match.groups()
        # Skip external URLs and anchors
        if link_path.startswith(("http://", "https://", "#", "mailto:")):
            continue
        # Resolve relative link
        if link_path.startswith("/"):
            continue  # Skip absolute paths
        target = (file_path.parent / link_path).resolve()
        if not target.exists():
            issues.append({
                "rule": "broken_link",
                "severity": "low",
                "file": str(file_path),
                "message": f"Broken link: [{link_text}]({link_path})"
            })
    return issues


def check_quality_score(content: str, file_path: Path) -> list[dict[str, str]]:
    """Check for quality score issues."""
    issues = []
    # Look for quality_score in frontmatter
    score_match = re.search(r'quality_score:\s*([\d.]+)', content)
    if score_match:
        score = float(score_match.group(1))
        if score < 0.3:
            issues.append({
                "rule": "low_quality_score",
                "severity": "medium",
                "file": str(file_path),
                "message": f"Quality score is {score} (below 0.3 threshold)"
            })
    return issues


def check_duplicate_titles(lessons: dict[str, str]) -> list[dict[str, str]]:
    """Check for duplicate titles across lessons."""
    issues = []
    title_map: dict[str, list[str]] = {}
    for file_path, content in lessons.items():
        lines = content.split("\n")
        for line in lines[:10]:
            if line.startswith("# "):
                title = line[2:].strip()
                if title not in title_map:
                    title_map[title] = []
                title_map[title].append(file_path)
                break
    for title, files in title_map.items():
        if len(files) > 1:
            issues.append({
                "rule": "duplicate_title",
                "severity": "medium",
                "file": ", ".join(files),
                "message": f"Duplicate title: '{title}'"
            })
    return issues


def lint_lesson(file_path: Path, lessons_dir: Path) -> list[dict[str, str]]:
    """Lint a single lesson file."""
    content = file_path.read_text(encoding="utf-8")
    issues = []
    issues.extend(check_frontmatter(content, file_path))
    issues.extend(check_title(content, file_path))
    issues.extend(check_length(content, file_path))
    issues.extend(check_links(content, file_path, lessons_dir))
    issues.extend(check_quality_score(content, file_path))
    return issues


def main() -> int:
    """Main entry point."""
    import argparse
    parser = argparse.ArgumentParser(description="Lesson lint / health check")
    parser.add_argument("--lessons-dir", default="lessons", help="Lessons directory")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument("--fail-on", choices=["high", "medium", "low"], default="high",
                        help="Fail on issues of this severity or higher")
    args = parser.parse_args()

    lessons_dir = Path(args.lessons_dir)
    if not lessons_dir.exists():
        print(f"Error: {lessons_dir} not found", file=sys.stderr)
        return 1

    # Collect all lesson files
    lesson_files = list(lessons_dir.rglob("*.md"))
    if not lesson_files:
        print(f"No .md files found in {lessons_dir}", file=sys.stderr)
        return 1

    # Load all lessons for duplicate check
    lessons: dict[str, str] = {}
    for f in lesson_files:
        try:
            lessons[str(f)] = f.read_text(encoding="utf-8")
        except Exception as e:
            print(f"Warning: Could not read {f}: {e}", file=sys.stderr)

    # Run all checks
    all_issues: list[dict[str, str]] = []

    # Single-file checks
    for file_path in lesson_files:
        try:
            all_issues.extend(lint_lesson(file_path, lessons_dir))
        except Exception as e:
            all_issues.append({
                "rule": "read_error",
                "severity": "high",
                "file": str(file_path),
                "message": f"Error reading file: {e}"
            })

    # Cross-file checks
    all_issues.extend(check_duplicate_titles(lessons))

    # Sort by severity
    severity_order = {"high": 0, "medium": 1, "low": 2}
    all_issues.sort(key=lambda x: severity_order.get(x.get("severity", "low"), 3))

    # Output
    if args.json:
        print(json.dumps(all_issues, indent=2))
    else:
        if not all_issues:
            print("[OK] No issues found!")
            return 0

        print(f"## Lesson Lint Report\n")
        print(f"**Checked:** {len(lesson_files)} files\n")

        # Count by severity
        high = sum(1 for i in all_issues if i.get("severity") == "high")
        medium = sum(1 for i in all_issues if i.get("severity") == "medium")
        low = sum(1 for i in all_issues if i.get("severity") == "low")
        print(f"**Issues:** {high} high, {medium} medium, {low} low\n")

        for issue in all_issues:
            severity = issue.get("severity", "unknown")
            icon = {"high": "[HIGH]", "medium": "[MED]", "low": "[LOW]"}.get(severity, "[???]")
            print(f"{icon} **{issue.get('rule', 'unknown')}** ({severity})")
            print(f"   File: {issue.get('file', 'unknown')}")
            print(f"   {issue.get('message', 'No message')}")
            print()

    # Determine exit code
    severity_levels = {"high": 0, "medium": 1, "low": 2}
    fail_level = severity_levels.get(args.fail_on, 0)
    has_failures = any(
        severity_levels.get(i.get("severity", "low"), 3) <= fail_level
        for i in all_issues
    )
    return 1 if has_failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
