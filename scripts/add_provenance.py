#!/usr/bin/env python3
"""Add provenance metadata to contrib lessons without it."""

import os
import re
import subprocess
import sys
from pathlib import Path
from datetime import datetime

# Auto-detect repo root from script location
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
CONTRIB_DIR = REPO_ROOT / "lessons" / "contrib"
BATCH_SIZE = 30

def get_git_history(filepath):
    """Get git author and date for a file."""
    try:
        result = subprocess.run(
            ["git", "log", "--follow", "--format=%an|%ai", "--", filepath],
            capture_output=True, text=True, cwd=str(REPO_ROOT)
        )
        if result.stdout.strip():
            lines = result.stdout.strip().split("\n")
            last_line = lines[-1]
            parts = last_line.split("|", 1)
            author = parts[0] if parts else ""
            date_str = parts[1] if len(parts) > 1 else ""
            # Extract YYYY-MM-DD
            date_match = re.match(r"(\d{4}-\d{2}-\d{2})", date_str)
            date = date_match.group(1) if date_match else ""
            return author, date
    except Exception:
        pass
    return "", ""

def determine_provenance_source(source_field, contributor):
    """Determine provenance source type from the source field."""
    if not source_field:
        return "internal"

    source_lower = source_field.lower()

    # GitHub PR sources
    if any(x in source_lower for x in ["github", "pr", "pull request", "merge"]):
        return "github-pr"

    # Known contributors -> treat as github-pr
    known_contributors = ["zsxh1990", "pdl", "codex", "claude", "agent"]
    if any(x in source_lower for x in known_contributors):
        return "github-pr"

    # MCP/intake sources
    if any(x in source_lower for x in ["mcp", "intake"]):
        return "mcp-intake"

    # Forum/colleague sources
    if any(x in source_lower for x in ["forum", "robot-forum", "segmentfault", "v2ex",
                                         "brgsk", "elastic", "csdn", "juejin", "zhihu"]):
        return "colleague-memory"

    # Bootstrap/internal sources
    if any(x in source_lower for x in ["bootstrap", "internal", "practical", "observed"]):
        return "internal"

    # Default to colleague-memory for external sources
    if source_lower.startswith("http") or "." in source_lower:
        return "colleague-memory"

    return "internal"

def determine_evidence(provenance_source):
    """Determine evidence type based on provenance source."""
    if provenance_source == "github-pr":
        return "pr-merged"
    elif provenance_source == "mcp-intake":
        return "pre-ingest-reuse"
    else:
        return "post-publication"

def extract_frontmatter(content):
    """Extract frontmatter fields from content."""
    lines = content.split("\n")

    # Detect frontmatter type
    if lines[0].strip() == "---":
        # YAML frontmatter
        end_idx = -1
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                end_idx = i
                break

        if end_idx == -1:
            return None, -1, {}

        fields = {}
        for i in range(1, end_idx):
            line = lines[i].strip()
            # Match key: value patterns
            match = re.match(r'^(\w[\w_-]*):\s*"?([^"]*?)"?\s*$', line)
            if match:
                fields[match.group(1)] = match.group(2)

        return "yaml", end_idx, fields

    elif lines[0].strip().startswith("{"):
        # JSON frontmatter
        json_content = ""
        end_idx = -1
        for i in range(len(lines)):
            json_content += lines[i]
            if lines[i].strip() == "}":
                end_idx = i
                break

        if end_idx == -1:
            return None, -1, {}

        try:
            import json
            fields = json.loads(json_content)
            return "json", end_idx, fields
        except (json.JSONDecodeError, ValueError):
            return None, -1, {}

    return None, -1, {}

def insert_provenance(content, fm_type, end_idx, provenance_data):
    """Insert provenance block into frontmatter."""
    provenance_block = f"""provenance:
  source: "{provenance_data['source']}"
  contributor: "{provenance_data['contributor']}"
  merged_at: "{provenance_data['merged_at']}"
  evidence: "{provenance_data['evidence']}\""""

    if fm_type == "yaml":
        lines = content.split("\n")
        # Insert before closing ---
        new_lines = lines[:end_idx] + [provenance_block] + lines[end_idx:]
        return "\n".join(new_lines)

    elif fm_type == "json":
        # Convert JSON to YAML and insert
        # This is more complex - we'd need to rebuild the frontmatter
        # For now, skip JSON files
        return None

    return None

def main():
    # Get all .md files
    all_lessons = list(CONTRIB_DIR.glob("*.md"))
    all_lessons = [f for f in all_lessons if f.name != "README.md"]

    # Filter out lessons with provenance
    lessons_without = []
    for lesson in all_lessons:
        content = lesson.read_text(encoding="utf-8")
        if "provenance:" not in content:
            lessons_without.append(lesson)

    print(f"Total contrib lessons: {len(all_lessons)}")
    print(f"Lessons with provenance: {len(all_lessons) - len(lessons_without)}")
    print(f"Lessons needing provenance: {len(lessons_without)}")
    print(f"Processing batch of {min(BATCH_SIZE, len(lessons_without))}...")
    print()

    results = []
    batch = lessons_without[:BATCH_SIZE]

    for i, lesson in enumerate(batch, 1):
        print(f"[{i}/{len(batch)}] {lesson.name}")

        content = lesson.read_text(encoding="utf-8")
        fm_type, end_idx, fields = extract_frontmatter(content)

        if fm_type is None:
            print(f"  Warning: Could not parse frontmatter, skipping")
            continue

        if fm_type == "json":
            print(f"  Warning: JSON frontmatter not supported yet, skipping")
            continue

        source = fields.get("source", "")
        created = fields.get("created", "")
        contributor = fields.get("domain_expert", "") or fields.get("contributor", "")

        # Get git history
        git_author, git_date = get_git_history(f"lessons/contrib/{lesson.name}")

        # Determine provenance
        provenance_source = determine_provenance_source(source, contributor)
        evidence = determine_evidence(provenance_source)

        # Use contributor from frontmatter, fallback to git
        if not contributor and git_author:
            contributor = git_author
        if not contributor:
            contributor = "unknown"

        # Use created date, fallback to git date
        merged_at = created or git_date or "2026-07-01"

        provenance_data = {
            "source": provenance_source,
            "contributor": contributor,
            "merged_at": merged_at,
            "evidence": evidence
        }

        # Insert provenance
        new_content = insert_provenance(content, fm_type, end_idx, provenance_data)
        if new_content is None:
            print(f"  Warning: Failed to insert provenance")
            continue

        # Write back
        lesson.write_text(new_content, encoding="utf-8")

        results.append({
            "file": lesson.name,
            "source": source,
            "contributor": contributor,
            "merged_at": merged_at,
            "provenance_source": provenance_source,
            "evidence": evidence
        })

        print(f"  -> Added: {provenance_source} | {contributor} | {merged_at} | {evidence}")

    # Summary
    print()
    print("=== Summary ===")
    print(f"Processed: {len(results)} lessons")

    # Count by provenance source
    source_counts = {}
    for r in results:
        src = r["provenance_source"]
        source_counts[src] = source_counts.get(src, 0) + 1
    print()
    print("Provenance sources:")
    for src, count in sorted(source_counts.items()):
        print(f"  {src}: {count}")

    # Count by evidence
    evidence_counts = {}
    for r in results:
        ev = r["evidence"]
        evidence_counts[ev] = evidence_counts.get(ev, 0) + 1
    print()
    print("Evidence types:")
    for ev, count in sorted(evidence_counts.items()):
        print(f"  {ev}: {count}")

if __name__ == "__main__":
    main()
