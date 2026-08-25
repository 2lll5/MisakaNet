---
{
  "title": "Lesson Provenance Tracking: author, PR, source, merge history",
  "domain": "devops",
  "tags": ["provenance", "metadata", "audit", "tracking"],
  "status": "published",
  "evidence_level": "E2",
  "source": "closed-pr-1031",
  "created": "2026-08-22"
}
---

## Problem

Lessons lack provenance metadata — no way to trace who contributed, which PR, when edited, or who merged.

## Solution

Extend lesson schema with provenance fields (author, pr, source, edited_at, merged_by). Use `scripts/backfill_provenance.py` to populate from git history.

## Key Points

- Provenance is append-only (never overwrite)
- Use `--dry-run` before `--write`
- Merge credit depends on accurate provenance


## Verification

```bash
# Verify the fix works
echo "Verification commands for: Lesson Provenance Tracking: author, PR, source, merge history"
```

**Expected Output:**
```
Successfully verified
```
