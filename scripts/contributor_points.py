#!/usr/bin/env python3
"""Non-transferable contributor reputation points ledger (Issue #819).

The JSON ledger is the source of truth. Every signal has a stable event id, so
workflow retries are idempotent. Writes are locked and atomic.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import html
import json
import os
import re
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DATA_FILE = REPO / "data" / "contributor-points.json"
LOCK_FILE = REPO / "data" / ".contributor-points.lock"
LEADERBOARD = REPO / "docs" / "leaderboard.html"
CONTRIBUTORS_DIR = REPO / "docs" / "contributors"
README = REPO / "README.md"
README_START = "<!-- contributor-points:start -->"
README_END = "<!-- contributor-points:end -->"

RULES = {
    "lesson_merge": 10,
    "search_hit": 1,
    "helpful": 3,
    "evidence_e2": 5,
    "stale_fix": 5,
    "maintenance": 3,
    "social_referral": 15,
    "not_helpful": -2,
    "lesson_deleted": -10,
}
CONTRIBUTION_EVENTS = {"lesson_merge", "evidence_e2", "stale_fix", "maintenance", "social_referral"}
DAILY_CAP = 50
NEW_ACCOUNT_CAP = 20
NEW_ACCOUNT_DAYS = 7
FREEZE_DAYS = 365


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def parse_time(value: str | None) -> datetime:
    if not value:
        return utcnow()
    value = value.replace("Z", "+00:00")
    result = datetime.fromisoformat(value)
    return result if result.tzinfo else result.replace(tzinfo=timezone.utc)


def empty_ledger() -> dict:
    return {
        "schema_version": 1,
        "updated_at": None,
        "policy": {
            "non_transferable": True,
            "cash_value": False,
            "redeemable": False,
            "on_chain": False,
            "daily_cap": DAILY_CAP,
            "new_account_cap": NEW_ACCOUNT_CAP,
            "new_account_days": NEW_ACCOUNT_DAYS,
            "freeze_after_inactive_days": FREEZE_DAYS,
        },
        "contributors": {},
        "processed_event_ids": [],
    }


def load_ledger(path: Path = DATA_FILE) -> dict:
    if not path.exists():
        return empty_ledger()
    data = json.loads(path.read_text(encoding="utf-8"))
    data.setdefault("contributors", {})
    data.setdefault("processed_event_ids", [])
    return data


def atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _safe_username(value: str) -> str:
    value = value.strip().lstrip("@")
    if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})", value):
        raise ValueError("invalid GitHub username")
    return value


def _event_id(
    event_type: str,
    contributor: str,
    lesson_id: str,
    actor_id: str,
    query_hash: str,
    timestamp: str,
) -> str:
    raw = "\0".join((event_type, contributor.lower(), lesson_id, actor_id, query_hash, timestamp))
    return hashlib.sha256(raw.encode()).hexdigest()


def record_event(
    ledger: dict,
    *,
    event_type: str,
    contributor: str,
    lesson_id: str = "",
    actor_id: str = "",
    query_hash: str = "",
    timestamp: str | None = None,
    event_id: str | None = None,
    account_created: str | None = None,
) -> tuple[dict, bool, str]:
    if event_type not in RULES:
        raise ValueError(f"unknown event type: {event_type}")
    contributor = _safe_username(contributor)
    now = parse_time(timestamp)
    timestamp = now.isoformat().replace("+00:00", "Z")
    event_id = event_id or _event_id(
        event_type, contributor, lesson_id, actor_id, query_hash, timestamp
    )
    if event_id in ledger["processed_event_ids"]:
        return ledger, False, "duplicate event id"

    account = ledger["contributors"].setdefault(
        contributor,
        {
            "points": 0,
            "frozen": False,
            "last_contribution_at": None,
            "account_created_at": account_created,
            "events": [],
        },
    )
    if account_created and not account.get("account_created_at"):
        account["account_created_at"] = account_created

    # One helpful point event per lesson and voter, forever.
    if (
        event_type == "helpful"
        and actor_id
        and any(
            e["type"] == "helpful"
            and e.get("lesson_id") == lesson_id
            and e.get("actor_id") == actor_id
            for e in account["events"]
        )
    ):
        return ledger, False, "duplicate helpful vote"

    # One search hit for the same lesson/query during any rolling 24-hour window.
    if (
        event_type == "search_hit"
        and query_hash
        and any(
            e["type"] == "search_hit"
            and e.get("lesson_id") == lesson_id
            and e.get("query_hash") == query_hash
            and now - parse_time(e["timestamp"]) < timedelta(hours=24)
            for e in account["events"]
        )
    ):
        return ledger, False, "duplicate search hit"

    last = account.get("last_contribution_at")
    inactive = bool(last and now - parse_time(last) >= timedelta(days=FREEZE_DAYS))
    if inactive and event_type not in CONTRIBUTION_EVENTS:
        account["frozen"] = True
        return ledger, False, "account frozen after 12 months without a contribution"
    if event_type in CONTRIBUTION_EVENTS:
        account["last_contribution_at"] = timestamp
        account["frozen"] = False

    requested = RULES[event_type]
    awarded = requested
    if requested > 0:
        day = now.date()
        earned_today = sum(
            max(0, int(e["points"]))
            for e in account["events"]
            if parse_time(e["timestamp"]).date() == day
        )
        cap = DAILY_CAP
        created = account.get("account_created_at")
        if created and now - parse_time(created) < timedelta(days=NEW_ACCOUNT_DAYS):
            cap = min(cap, NEW_ACCOUNT_CAP)
        awarded = max(0, min(requested, cap - earned_today))

    event = {
        "id": event_id,
        "type": event_type,
        "points": awarded,
        "requested_points": requested,
        "timestamp": timestamp,
        "lesson_id": lesson_id,
    }
    if actor_id:
        event["actor_id"] = actor_id
    if query_hash:
        event["query_hash"] = query_hash
    account["events"].append(event)
    account["points"] = max(0, int(account["points"]) + awarded)
    ledger["processed_event_ids"].append(event_id)
    ledger["updated_at"] = timestamp
    return (
        ledger,
        True,
        "recorded" if awarded == requested else f"recorded with daily cap ({awarded}/{requested})",
    )


def _breakdown(account: dict) -> dict[str, int]:
    result: dict[str, int] = {}
    for event in account["events"]:
        result[event["type"]] = result.get(event["type"], 0) + int(event["points"])
    return result


def _page(title: str, body: str) -> str:
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width">'
        f"<title>{html.escape(title)}</title><style>"
        "body{font:16px system-ui;max-width:900px;margin:3rem auto;padding:0 1rem;"
        "color:#e6edf3;background:#0d1117}a{color:#58a6ff}"
        "table{border-collapse:collapse;width:100%}th,td{padding:.65rem;"
        "border-bottom:1px solid #30363d;text-align:left}.notice{padding:1rem;"
        "background:#161b22;border:1px solid #30363d;border-radius:8px}"
        f"</style></head><body>{body}</body></html>\n"
    )


def build_pages(ledger: dict, repo: Path = REPO) -> None:
    leaderboard = repo / "docs" / "leaderboard.html"
    contributors_dir = repo / "docs" / "contributors"
    readme = repo / "README.md"
    ranked = sorted(
        ledger["contributors"].items(), key=lambda item: (-int(item[1]["points"]), item[0].lower())
    )
    rows = (
        "".join(
            "<tr>"
            f"<td>{rank}</td>"
            f'<td><a href="contributors/{html.escape(name)}.html">{html.escape(name)}</a></td>'
            f'<td>{account["points"]}</td>'
            f'<td>{"frozen" if account.get("frozen") else "active"}</td>'
            "</tr>"
            for rank, (name, account) in enumerate(ranked, 1)
        )
        or '<tr><td colspan="4">No points recorded yet.</td></tr>'
    )
    body = (
        '<h1>Contributor reputation leaderboard</h1><p class="notice">'
        "Project reputation only. Points have no cash value, are non-transferable, "
        "non-redeemable, and are not a token or financial asset.</p>"
        "<table><thead><tr><th>Rank</th><th>Contributor</th>"
        "<th>Points</th><th>Status</th></tr></thead><tbody>"
        + rows
        + '</tbody></table><p><a href="contributor-points.md">Rules and safeguards</a></p>'
    )
    leaderboard.write_text(_page("Contributor leaderboard", body), encoding="utf-8")

    contributors_dir.mkdir(parents=True, exist_ok=True)
    for name, account in ranked:
        details = "".join(
            f"<tr><td>{html.escape(kind)}</td><td>{points:+d}</td></tr>"
            for kind, points in sorted(_breakdown(account).items())
        )
        body = (
            '<p><a href="../leaderboard.html">← Leaderboard</a></p>'
            f"<h1>{html.escape(name)}</h1>"
            f'<h2>{account["points"]} reputation points</h2>'
            '<p class="notice">Non-transferable project reputation. '
            "No cash value and no redemption.</p>"
            "<table><thead><tr><th>Signal</th><th>Points</th></tr></thead>"
            f"<tbody>{details}</tbody></table>"
        )
        (contributors_dir / f"{name}.html").write_text(
            _page(f"{name} contributor points", body), encoding="utf-8"
        )

    top = ranked[:10]
    lines = [
        "### Top 10 contributors by reputation points",
        "",
        "| Rank | Contributor | Points |",
        "|---:|---|---:|",
    ]
    lines.extend(
        f"| {i} | [{name}](docs/contributors/{name}.html) | {account['points']} |"
        for i, (name, account) in enumerate(top, 1)
    )
    if not top:
        lines.append("| — | No points recorded yet | 0 |")
    block = README_START + "\n" + "\n".join(lines) + "\n" + README_END
    text = readme.read_text(encoding="utf-8")
    pattern = re.compile(re.escape(README_START) + ".*?" + re.escape(README_END), re.DOTALL)
    text = (
        pattern.sub(block, text) if pattern.search(text) else text.rstrip() + "\n\n" + block + "\n"
    )
    readme.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    record = sub.add_parser("record")
    record.add_argument("--type", required=True, choices=sorted(RULES))
    record.add_argument("--contributor", required=True)
    record.add_argument("--lesson-id", default="")
    record.add_argument("--actor-id", default="")
    record.add_argument("--query-hash", default="")
    record.add_argument("--timestamp")
    record.add_argument("--event-id")
    record.add_argument("--account-created")
    sub.add_parser("build")

    args = parser.parse_args()
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOCK_FILE.open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        ledger = load_ledger()
        if args.command == "record":
            ledger, changed, message = record_event(
                ledger,
                event_type=args.type,
                contributor=args.contributor,
                lesson_id=args.lesson_id,
                actor_id=args.actor_id,
                query_hash=args.query_hash,
                timestamp=args.timestamp,
                event_id=args.event_id,
                account_created=args.account_created,
            )
            if changed:
                atomic_write(DATA_FILE, ledger)
            print(message)
        build_pages(ledger)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
