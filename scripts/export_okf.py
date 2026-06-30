#!/usr/bin/env python3
"""Export MisakaNet lessons to OKF (Open Knowledge Format) compatible JSONL.

Usage:
    python3 scripts/export_okf.py                    # export all lessons
    python3 scripts/export_okf.py --output data/okf/ # custom output dir
    python3 scripts/export_okf.py --domain devops    # filter by domain

Output: data/okf/lessons.jsonl (one JSON object per line)
Each line: {"type":"lesson","title":"...","description":"...","tags":[...],"timestamp":"...","domain":"...","source":"..."}
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LESSONS_DIR = REPO_ROOT / "lessons"
DEFAULT_OUTPUT = REPO_ROOT / "data" / "okf"


def extract_frontmatter(path: Path) -> dict | None:
    """Extract JSON or YAML frontmatter from a lesson file."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None

    # Try JSON frontmatter first
    import re
    m = re.match(r"^---\s*\n(\{.*?\})\n---", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass

    # Try YAML-like frontmatter
    m = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return None

    meta = {}
    for line in m.group(1).split("\n"):
        line = line.strip()
        if ":" not in line or line.startswith("{"):
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if val.startswith("[") and val.endswith("]"):
            try:
                meta[key] = json.loads(val.replace("'", '"'))
            except json.JSONDecodeError:
                meta[key] = [v.strip().strip('"').strip("'") for v in val[1:-1].split(",")]
        else:
            meta[key] = val
    return meta


def extract_description(text: str, max_len: int = 200) -> str:
    """Extract a short description from the lesson body."""
    import re
    # Remove frontmatter
    m = re.match(r"^---.*?---\s*", text, re.DOTALL)
    if m:
        text = text[m.end():]

    # Find first non-heading, non-empty line
    for line in text.split("\n"):
        line = line.strip()
        if line and not line.startswith("#") and not line.startswith("```"):
            # Truncate
            if len(line) > max_len:
                return line[:max_len] + "..."
            return line
    return ""


def lesson_to_okf(path: Path, domain_filter: str | None = None) -> dict | None:
    """Convert a lesson file to OKF format."""
    meta = extract_frontmatter(path)
    if not meta:
        return None

    domain = meta.get("domain", "general")
    if domain_filter and domain != domain_filter:
        return None

    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None

    # Extract description from body if not in frontmatter
    description = meta.get("description", "")
    if not description:
        description = extract_description(text)

    # Normalize tags
    tags = meta.get("tags", [])
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",")]

    # Build OKF record
    okf = {
        "type": "lesson",
        "title": meta.get("title", path.stem),
        "description": description,
        "tags": tags,
        "timestamp": meta.get("created", meta.get("updated", "")),
        "domain": domain,
        "source": meta.get("source", ""),
        "status": meta.get("status", "published"),
        "path": str(path.relative_to(REPO_ROOT)),
    }

    # Optional fields
    if meta.get("verified_date"):
        okf["verified_date"] = meta["verified_date"]
    if meta.get("domain_expert"):
        okf["domain_expert"] = meta["domain_expert"]

    return okf


def main():
    parser = argparse.ArgumentParser(description="Export MisakaNet lessons to OKF format")
    parser.add_argument("--output", type=str, default=str(DEFAULT_OUTPUT), help="Output directory")
    parser.add_argument("--domain", type=str, default=None, help="Filter by domain")
    parser.add_argument("--format", choices=["jsonl", "json"], default="jsonl", help="Output format")
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Collect all lesson files
    lesson_files = []
    for subdir in ["core", "contrib"]:
        d = LESSONS_DIR / subdir
        if d.exists():
            lesson_files.extend(sorted(d.glob("*.md")))

    # Convert to OKF
    okf_records = []
    skipped = 0
    for path in lesson_files:
        if path.name == "README.md":
            continue
        record = lesson_to_okf(path, domain_filter=args.domain)
        if record:
            okf_records.append(record)
        else:
            skipped += 1

    # Write output
    if args.format == "jsonl":
        output_file = output_dir / "lessons.jsonl"
        with open(output_file, "w", encoding="utf-8") as f:
            for record in okf_records:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
    else:
        output_file = output_dir / "lessons.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(okf_records, f, ensure_ascii=False, indent=2)

    # Summary
    print(f"Exported {len(okf_records)} lessons to {output_file}")
    if skipped:
        print(f"Skipped {skipped} files (no valid frontmatter)")
    print(f"Domains: {len(set(r['domain'] for r in okf_records))}")
    print(f"Format: {args.format}")

    # Validate OKF required fields
    missing = []
    for r in okf_records:
        for field in ["type", "title", "description", "tags", "timestamp"]:
            if not r.get(field):
                missing.append(f"{r.get('path', '?')}: missing {field}")
    if missing:
        print(f"\nWarnings ({len(missing)} missing fields):")
        for m in missing[:10]:
            print(f"  {m}")
        if len(missing) > 10:
            print(f"  ... and {len(missing) - 10} more")


if __name__ == "__main__":
    main()
