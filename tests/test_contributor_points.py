"""Tests for the non-transferable contributor points ledger."""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.contributor_points import empty_ledger, record_event


def add(ledger, kind, **kwargs):
    return record_event(ledger, event_type=kind, contributor="alice", **kwargs)


def test_rules_and_idempotency():
    ledger = empty_ledger()
    ledger, changed, _ = add(
        ledger,
        "lesson_merge",
        lesson_id="one",
        event_id="merge-1",
        timestamp="2026-08-01T00:00:00Z",
    )
    assert changed and ledger["contributors"]["alice"]["points"] == 10
    ledger, changed, _ = add(
        ledger,
        "lesson_merge",
        lesson_id="one",
        event_id="merge-1",
        timestamp="2026-08-01T00:00:00Z",
    )
    assert not changed and ledger["contributors"]["alice"]["points"] == 10


def test_helpful_dedup_by_actor_and_lesson():
    ledger = empty_ledger()
    ledger, changed, _ = add(
        ledger,
        "helpful",
        lesson_id="one",
        actor_id="voter-hash",
        event_id="h1",
        timestamp="2026-08-01T00:00:00Z",
    )
    assert changed
    ledger, changed, reason = add(
        ledger,
        "helpful",
        lesson_id="one",
        actor_id="voter-hash",
        event_id="h2",
        timestamp="2026-08-02T00:00:00Z",
    )
    assert not changed and "duplicate" in reason


def test_search_dedup_rolling_24_hours():
    ledger = empty_ledger()
    ledger, changed, _ = add(
        ledger,
        "search_hit",
        lesson_id="one",
        query_hash="query",
        event_id="s1",
        timestamp="2026-08-01T12:00:00Z",
    )
    assert changed
    ledger, changed, _ = add(
        ledger,
        "search_hit",
        lesson_id="one",
        query_hash="query",
        event_id="s2",
        timestamp="2026-08-02T11:59:00Z",
    )
    assert not changed
    ledger, changed, _ = add(
        ledger,
        "search_hit",
        lesson_id="one",
        query_hash="query",
        event_id="s3",
        timestamp="2026-08-02T12:01:00Z",
    )
    assert changed


def test_daily_and_new_account_caps():
    ledger = empty_ledger()
    for i in range(6):
        ledger, _, _ = add(
            ledger, "social_referral", event_id=f"r{i}", timestamp=f"2026-08-01T0{i}:00:00Z"
        )
    assert ledger["contributors"]["alice"]["points"] == 50

    young = empty_ledger()
    for i in range(3):
        young, _, _ = add(
            young,
            "lesson_merge",
            event_id=f"m{i}",
            timestamp=f"2026-08-01T0{i}:00:00Z",
            account_created="2026-07-31T00:00:00Z",
        )
    assert young["contributors"]["alice"]["points"] == 20


def test_freeze_and_unfreeze():
    ledger = empty_ledger()
    old = datetime(2025, 1, 1, tzinfo=timezone.utc)
    ledger, _, _ = add(ledger, "lesson_merge", event_id="old", timestamp=old.isoformat())
    later = old + timedelta(days=366)
    ledger, changed, reason = add(
        ledger,
        "search_hit",
        lesson_id="x",
        query_hash="q",
        event_id="frozen",
        timestamp=later.isoformat(),
    )
    assert not changed and "frozen" in reason
    ledger, changed, _ = add(
        ledger, "maintenance", lesson_id="x", event_id="fresh", timestamp=later.isoformat()
    )
    assert changed and not ledger["contributors"]["alice"]["frozen"]


def test_penalties_never_make_negative():
    ledger = empty_ledger()
    ledger, changed, _ = add(
        ledger, "lesson_deleted", lesson_id="x", event_id="d1", timestamp="2026-08-01T00:00:00Z"
    )
    assert changed and ledger["contributors"]["alice"]["points"] == 0
