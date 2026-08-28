#!/usr/bin/env python3
"""
Sync MisakaNet lessons (repo source-of-truth) into Cloudflare D1 (PRD ④).

Pipeline: lessons/*.md  →  parse  →  upsert SQL  →  wrangler d1 execute

Design:
  - The Git repo stays the authoritative source (history/review/contribution);
    D1 is the serving layer (HTTP/MCP direct query, no clone required).
  - Idempotent: upsert by lesson id; re-runs never duplicate.
  - Emits `INSERT ... ON CONFLICT(id) DO UPDATE` statements so it works with
    `wrangler d1 execute <db> --remote --file=-`.

Usage:
    # 1. Create the database once:
    #    wrangler d1 create misakanet-db
    #    (then put database_id into workers/wrangler.toml)

    # 2. Apply schema once:
    #    wrangler d1 execute misakanet-db --remote --file=workers/d1/schema.sql

    # 3. Sync lessons (dry run first, then execute):
    #    python3 scripts/sync_lessons_to_d1.py --db misakanet-db --dry-run
    #    python3 scripts/sync_lessons_to_d1.py --db misakanet-db --execute
    #    # or pipe: python3 scripts/sync_lessons_to_d1.py --sql | wrangler d1 execute misakanet-db --remote --file=-

    # 4. Reconcile (verify repo == D1 via checksums):
    #    python3 scripts/sync_lessons_to_d1.py --db misakanet-db --reconcile

Auth: CLOUDFLARE_API_TOKEN + CLOUDFLARE_ACCOUNT_ID env (CI), or wrangler login (local).
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LESSONS_DIR = REPO / "lessons"
INDEXED_DIRS = ("core", "contrib")
EXCLUDED = {"README.md", "index.md", "TEMPLATE.md", "CONTRIBUTING.md"}

SECTION_ALIASES = {
    "problem": ["problem", "问题", "描述"],
    "root_cause": ["root cause", "根因", "原因", "根因分析"],
    "solution": ["solution", "fix", "修复", "解法", "方案", "正确做法", "修复方案"],
    "verification": ["verification", "verify", "验证", "验证方式"],
}


def parse_frontmatter(text: str) -> dict:
    """Parse lesson frontmatter: JSON first, then YAML fallback.

    Some lessons append a YAML-ish `provenance:` block after the JSON object
    inside the same frontmatter delimiters; raw_decode extracts only the
    leading JSON object. Newer lessons use plain YAML frontmatter — fall back
    to yaml.safe_load for those (mirrors update_lessons_json.py).
    """
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 4)
    if end == -1:
        return {}
    raw = text[4:end].strip()
    if raw.startswith("{"):
        try:
            return json.JSONDecoder().raw_decode(raw)[0]
        except (json.JSONDecodeError, ValueError):
            pass
    try:
        import yaml
        fm = yaml.safe_load(raw)
        if isinstance(fm, dict):
            return fm
    except Exception:
        pass
    return {}


def split_sections(body: str) -> dict:
    """Extract named sections from a lesson body by heading aliases."""
    out = {k: "" for k in SECTION_ALIASES}
    # Split on any ## heading, keep heading text for matching.
    parts = re.split(r"^##\s+(.+?)\s*$", body, flags=re.M)
    # parts[0] = preamble; then heading, content pairs.
    for i in range(1, len(parts) - 1, 2):
        heading = parts[i].strip().lower()
        content = parts[i + 1].strip()
        for key, aliases in SECTION_ALIASES.items():
            if any(a in heading for a in aliases) and not out[key]:
                out[key] = content[:2000]
    return out


def lesson_checksum(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


def parse_lesson(path: Path) -> dict | None:
    text = path.read_text(encoding="utf-8", errors="replace")
    if not text.strip():
        return None
    fm = parse_frontmatter(text)
    # YAML frontmatter may yield non-JSON types (date, etc.) — normalize
    fm = {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in fm.items()}
    # Body = everything after the closing --- of the frontmatter block
    end = text.find("\n---", 4)
    body = text[end + 4:] if end != -1 else text
    sections = split_sections(body)
    title = fm.get("title") or path.stem
    domain = fm.get("domain") or path.parent.name
    if isinstance(domain, list):
        domain = domain[0] if domain else path.parent.name
    tags = fm.get("tags", [])
    if not isinstance(tags, list):
        tags = [tags] if tags else []
    summary = fm.get("summary", "") or re.sub(r"\s+", " ", body).strip()[:200]
    return {
        "id": path.stem,
        "title": title,
        "domain": domain,
        "status": fm.get("status", "published"),
        "language": fm.get("language", "en"),
        "tags": json.dumps(tags, ensure_ascii=False),
        "path": path.relative_to(REPO).as_posix(),
        "problem": sections["problem"],
        "root_cause": sections["root_cause"],
        "solution": sections["solution"],
        "verification": sections["verification"],
        "content_md": body.strip()[:30000],
        "frontmatter": json.dumps(fm, ensure_ascii=False),
        "summary": summary,
        "created": fm.get("created", ""),
        "updated": fm.get("updated", ""),
        "checksum": lesson_checksum(text),
    }


def collect_lessons() -> list[dict]:
    lessons = []
    for sub in INDEXED_DIRS:
        d = LESSONS_DIR / sub
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.md")):
            if f.name in EXCLUDED or f.name.startswith("."):
                continue
            lesson = parse_lesson(f)
            if lesson:
                lessons.append(lesson)
    return lessons


def upsert_sql(lessons: list[dict]) -> str:
    cols = ["id", "title", "domain", "status", "language", "tags", "path",
            "problem", "root_cause", "solution", "verification", "content_md",
            "frontmatter", "summary", "created", "updated", "checksum", "synced_at"]
    now = "datetime('now')"
    stmts = [f"-- {len(lessons)} lessons parsed at {now}"]
    for l in lessons:
        vals = []
        for c in cols:
            if c == "synced_at":
                vals.append(now)
                continue
            v = l.get(c, "")
            if v is None:
                v = ""
            vals.append("'" + str(v).replace("'", "''") + "'")
        stmts.append(
            "INSERT INTO lessons (" + ", ".join(cols) + ") VALUES ("
            + ", ".join(vals) + ") "
            + "ON CONFLICT(id) DO UPDATE SET "
            + ", ".join(f"{c}=excluded.{c}" for c in cols if c != "id")
            + ";"
        )
    stmts.append(f"INSERT INTO lesson_sync_log (run_at, source_commit, total, upserted) "
                 f"VALUES ({now}, '{git_head()}', {len(lessons)}, {len(lessons)});")
    return "\n".join(stmts) + "\n"


def git_head() -> str:
    try:
        r = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                           capture_output=True, text=True, cwd=REPO, timeout=10)
        return r.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def main() -> int:
    ap = argparse.ArgumentParser(description="Sync lessons to Cloudflare D1")
    ap.add_argument("--db", default="misakanet-db", help="D1 database name")
    ap.add_argument("--sql", action="store_true", help="only emit SQL to stdout")
    ap.add_argument("--dry-run", action="store_true", help="parse + print summary, no execute")
    ap.add_argument("--execute", action="store_true", help="run wrangler d1 execute --remote")
    ap.add_argument("--reconcile", action="store_true", help="compare repo checksums vs D1")
    ap.add_argument("--output", help="write SQL to this file instead of stdout")
    args = ap.parse_args()

    lessons = collect_lessons()
    print(f"Parsed {len(lessons)} lessons from {LESSONS_DIR}", file=sys.stderr)

    if args.reconcile:
        repo = {l["id"]: l["checksum"] for l in lessons}
        print(f"Reconcile: {len(repo)} repo checksums (run D1 query to compare "
              f"SELECT id, checksum FROM lessons;)", file=sys.stderr)
        return 0

    sql = upsert_sql(lessons)

    if args.sql or args.output or not (args.execute or args.dry_run):
        if args.output:
            Path(args.output).write_text(sql, encoding="utf-8")
            print(f"SQL written to {args.output}", file=sys.stderr)
        else:
            sys.stdout.write(sql)
        return 0

    if args.dry_run:
        print(f"[dry-run] {len(lessons)} upserts would be executed against D1 "
              f"'{args.db}' (remote)", file=sys.stderr)
        return 0

    if args.execute:
        cmd = ["wrangler", "d1", "execute", args.db, "--remote", "--command", sql]
        print(f"Executing: {' '.join(cmd[:4])} ...", file=sys.stderr)
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO, timeout=600)
        sys.stdout.write(r.stdout)
        sys.stderr.write(r.stderr)
        return r.returncode

    return 0


if __name__ == "__main__":
    sys.exit(main())
