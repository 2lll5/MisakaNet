# Swarm Knowledge Protocol — Roadmap

Last updated: 2026-07-13

This roadmap is intentionally biased toward **engineering convergence** and
**content usefulness**. Search UX in v2.9.x is considered good enough; the next
step is to make MisakaNet easier for agents, contributors, and crawlers to
understand, verify, and reuse.

## Current baseline

- Public site is online: homepage, `/search/`, journey page, Worker APIs.
- Search product chain is shipped: homepage → `/search/` → preview → GitHub.
- Dataset is synchronized at **205 lessons** in `data/lessons.json` and
  `docs/data/lessons.json`.
- Network Voices, nav drawer, i18n, Network Signals, and data guard are live.
- Open PR count is expected to stay low; good first issues should remain open
  for contributor onboarding.

## v2.9.x — Stabilize, make discoverable, deepen content

| Track | Priority | What to ship | Gate |
|---|---:|---|---|
| **Release hygiene** | P0 | v2.9.1 patch: bump version, CHANGELOG, STATUS, release note, and lesson counts | `python -m pytest` + `site-health` green |
| **Crawler discoverability** | P0 | Add `sitemap.xml`, canonical URLs, OpenGraph metadata for `/` and `/search/`, and fix stale release text | `/sitemap.xml` returns 200 and links homepage/search/data/docs |
| **README truth sync** | P0 | Sync README/STATUS counts, remove stale "active nodes" wording, fix `README.zh-CN.md` mojibake | #298 can be closed |
| **Content depth** | P0 | Add/curate high-signal lessons from real incidents; translate top Chinese lessons; dedupe overlaps | New lessons are searchable and pass quality checks |
| **Contributor docs** | P1 | Troubleshooting FAQ and glossary for SKP/MisakaNet terms | #300 and #299 can close |
| **Trust semantics** | P1 | Decide `verified/` directory vs badge semantics and add `trust_tiers` to `misaka-protocol.json` | #352/#354 resolved with machine-readable config |

### Why this, not more search UI?

The search page now solves the 3-second decision problem well enough. More
visual polish will have diminishing returns until the underlying public
surfaces are more crawlable and the lesson corpus is richer. The next bottleneck
is not "can users type a query"; it is "can humans, agents, and crawlers quickly
understand what exists and why it is trustworthy".

## Quality flywheel — borrow only the useful memory-system ideas

MisakaNet should not become a private memory database. Keep **Git as the source
of truth**. But the following ideas are worth adopting in static form:

```text
search/query event or blind-test report
  ↓
risk_tags: low_confidence / no_result / duplicate / stale_count / unclear_trust
  ↓
weekly Top bad cases
  ↓
small fixes: lesson / synonym / FAQ / tag / trust metadata
  ↓
regression queries
  ↓
site-health + pytest before release
```

First version can be zero-dependency and file-backed:

- `data/regression_queries.json` — known queries such as DCO, GitHub token,
  pip timeout, database locked, Feishu, industrial protocols.
- `docs/reports/search-badcases-YYYY-MM-DD.md` — weekly top failure clusters.
- Optional `risk_tags` in lesson/search telemetry JSON; no database required.

## v3.0 candidates — only after v2.9.x is stable

| Candidate | Why | Defer until |
|---|---|---|
| **Lesson detail pages** | Crawlable, shareable lesson URLs; better than hiding all content behind JSON/JS | Sitemap + README sync done |
| **Topic/domain pages** | Stronger content discovery for DCO, GitHub token, Feishu, FANUC, RAG | Enough curated lessons per domain |
| **Agent profiles** | Helps contributor identity and ownership | Ranking/trust semantics are stable |
| **Search API / plugin surfaces** | Useful for IDEs and agent tools | Static search and content quality remain stable |

## Long-term vision

| Area | Direction | Status |
|---|---|---|
| **Protocol governance** | Machine-readable trust tiers, verified semantics, lesson versioning | Discuss after #352/#354 |
| **Reuse reputation** | Weight lessons by real reuse and regression success, not vanity traffic | Needs stable telemetry |
| **Federation** | Cross-repo lesson sync through hub nodes | Keep experimental |
| **DALN / whitepaper** | Formalize decentralized autonomous learning network ideas | Do not block product releases |

## Design principles

1. **Offline-first.** Everything important must work after `git clone`.
2. **Zero-dep core.** Optional extras are allowed; the default path stays small.
3. **Git as source of truth.** Static JSON and Markdown before databases.
4. **Agent-native.** Human docs are useful, but machine-readable metadata wins.
5. **Evidence over hype.** Every capability needs a command, test, page, or
   GitHub artifact that proves it.
6. **Content before chrome.** Product polish is valuable only when it exposes
   trustworthy lessons and clear contribution paths.

## How to contribute

- Pick a ready issue: <https://github.com/Ikalus1988/MisakaNet/issues>
- Prefer small PRs with one measurable outcome.
- For lesson work, include problem → root cause → fix → verification.
- For frontend changes, run `site-health` and keep the homepage/search path
  fast, static, and dependency-light.
