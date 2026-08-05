# Contributor reputation points

MisakaNet awards **non-transferable, off-chain project reputation** for useful lesson work.

> These points have **no cash value**, cannot be transferred or redeemed, are not a token or
> financial asset, and carry no promise of payment or future exchange. They exist only to show
> reputation inside the MisakaNet project.

## Rules

| Event | Points |
|---|---:|
| Lesson merged | +10 |
| Search hit | +1 |
| Unique helpful vote | +3 |
| Lesson reaches E2+ evidence | +5 |
| Stale lesson fixed | +5 |
| Translation, cleanup, or restructuring | +3 |
| Accepted social referral post | +15 |
| Not-helpful signal | -2 |
| Lesson deleted | -10 |

The canonical, auditable ledger is [`data/contributor-points.json`](../data/contributor-points.json).
`python3 scripts/contributor_points.py build` generates the [leaderboard](leaderboard.html),
per-contributor detail pages, and the README Top 10 table.

## Automation

* A merge to `main` records each newly added `lessons/core/*.md` or `lessons/contrib/*.md` file.
* Helpful votes and search hits submit idempotent `repository_dispatch` signals without blocking
  the search UI. The workflow records them and commits regenerated views.
* All retries are safe because every signal has a stable event ID. JSON writes use a process lock
  and atomic file replacement.

## Anti-abuse and inactivity

* Positive awards are capped at **50 points per contributor per UTC day**.
* Accounts less than 7 days old are capped at **20 points per UTC day**.
* The same user can award helpful points to a lesson only once.
* The same lesson/query pair earns one search-hit point in a rolling 24-hour window. Only a
  one-way query hash is stored; raw queries are never written to the ledger.
* After 12 months with no contribution event, reputation is frozen (not reduced). A new verified
  contribution unfreezes the account. Negative quality corrections may still apply.
* Point totals never fall below zero.

## Maintainer commands

```bash
python3 scripts/contributor_points.py record --type lesson_merge \
  --contributor octocat --lesson-id example --event-id merge-sha-example
python3 scripts/contributor_points.py record --type helpful \
  --contributor octocat --lesson-id example --actor-id hashed-voter-id
python3 scripts/contributor_points.py build
```
