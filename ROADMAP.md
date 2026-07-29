# MisakaNet 3-Month Roadmap

Last updated: 2026-07-29

This roadmap covers August-October 2026. It is biased toward one practical
flywheel:

```text
private intake -> classification -> maintainer demand board -> curated lesson/rescue/issue
```

MisakaNet should stay offline-first and Git-backed. External listings are useful
"amplifiers", not the product itself.

## Current baseline

- Release/distribution: PyPI `misakanet 2.12.2`, GitHub release `v2.12.2`,
  MCP Registry published, Glama indexed/scored, MCP Toplist badge live.
- Public site is online: homepage, `/search/`, journey page, Worker APIs, and
  lesson data endpoints are healthy.
- Corpus wording baseline: **244 indexed failure lessons**; avoid claiming
  all are verified unless also stating the verified count separately.
- Local MCP server exposes three tools: `misakanet_search`,
  `misakanet_get_lesson`, and `misakanet_submit_usage`.
- PR governance: DCO is mandatory. Do not deep-review or merge DCO-failing PRs.
- External listing posture: Glama/MCP Registry/MCP Toplist are stable; Smithery
  and GitHub `/mcp` inclusion are deferred until the product loop is stronger.

## August 2026 - v2.13.0: feedback intake loop

Goal: a sandbox, agent, or human can submit a private redacted failure report;
maintainers can classify and route it without exposing raw logs or prompts.

| Track | Priority | What to ship | Gate |
|---|---:|---|---|
| **Curl-first intake** | P0 | `POST /api/intake` for explicit opt-in, private, redacted feedback | `curl` smoke test returns an intake id; no raw log/prompt/file content stored |
| **Classifier integration** | P0 | Route intake into `lesson`, `rescue`, `bug`, or `noise` | Unit tests cover redaction, empty payloads, and category routing |
| **Demand board** | P0 | Maintainer-facing board of intake clusters and next actions | Board shows pending/reviewed/routed items from fixture data |
| **Feedback CLI path** | P1 | Search/CLI `--feedback` path that reuses the same policy boundaries | Local JSONL or API submission is explicit and documented |
| **MCP tool clarity** | P1 | Keep tool descriptions aligned with side effects, auth, rate limits, input/output schema | `tools/list` exposes all 3 tools with operating-contract descriptions |
| **PR hygiene** | P1 | Work through DCO-clean intake PRs in order: #623 -> #624 -> #622 | No DCO, no merge; competing PRs use first clean + scoped + tested wins |

Out of scope for v2.13.0:

- Auto-publishing public lessons
- Auto-opening GitHub issues
- Auto-submitting PRs
- Full Danmaku launch
- Re-publishing Smithery or bumping registry versions just for listing polish

## September 2026 - v2.14.0: curation and trust quality

Goal: turn intake into trustworthy public knowledge without metric drift or
lesson spam.

| Track | Priority | What to ship | Gate |
|---|---:|---|---|
| **Review queue** | P0 | Intake review states: private, accepted, rejected, needs-repro, converted | Maintainer can trace one intake to one lesson/rescue/issue decision |
| **Lesson trust semantics** | P0 | Clarify `indexed`, `published`, and `verified` wording across README/docs/site | README, site counters, and generated data agree on counts and labels |
| **Regression queries** | P1 | `data/regression_queries.json` for DCO, GitHub token, pip timeout, MCP, Feishu, FANUC, WSL | Search tests include representative real failure queries |
| **Duplicate governance** | P1 | Continue duplicate/stale lesson policy without blocking useful contributions | New lessons pass quality checks and do not duplicate existing lessons silently |
| **Frontend health** | P1 | Keep search, registration, journey, and API health in every public UX change | `site-health` green before release notes |
| **Docs cleanup** | P2 | Remove or archive stale generated/runtime artifacts and obsolete examples via separate small PRs | Each cleanup PR has one purpose and no generated data churn |

## October 2026 - v2.15/v3.0 readiness: distribution confidence

Goal: make external discovery channels reflect a stable product, not a vanity
badge collection.

| Track | Priority | What to ship | Gate |
|---|---:|---|---|
| **MCP runtime verification** | P0 | Verify deployed/listed runtime `tools/list` sees all intended tools | Evidence from local smoke + listed runtime scan or Glama refresh |
| **Registry metadata refresh** | P1 | Next real release may add clearer `server.json` title/description and aligned counts | Only publish a new version when there is a real release, not duplicate-version churn |
| **Glama quality follow-up** | P1 | Improve MCP tool coherence/completeness where it maps to real behavior | Glama score page updates without breaking existing install path |
| **GitHub `/mcp` candidacy** | P2 | Reconsider email nomination after v2.13 loop is live and metadata is clean | Official Registry active + Glama evaluated + concise use-case evidence + no version mismatch |
| **Smithery** | P2 | Keep paused unless there is a real `.mcpb` or public MCP endpoint with no 403 scan blockers | No placeholder URLs; no duplicate-version publish attempts |
| **Adoption evidence** | P2 | Separate traffic metrics from lesson-use evidence | Release notes say what was measured: views/clones/helpful/intake, without overclaiming adoption |

## External channel policy (external amplifiers)

External surfaces help users discover MisakaNet, but they must not drive rushed
architecture changes.

| Channel | Current stance | Do next | Do not do |
|---|---|---|---|
| **Glama** | Keep stable | Maintain score badge and improve real tool descriptions | Do not churn versions only to chase score |
| **MCP Registry** | Published | Update metadata on next real release | Do not republish duplicate `2.12.2` |
| **MCP Toplist** | Badge live | Treat as discovery signal | Do not call it official recommendation |
| **Smithery** | Paused | Revisit only with real bundle/endpoint | Do not publish placeholder URL or break Glama path |
| **GitHub `/mcp`** | Deferred | Reassess after v2.13 intake is demonstrable | Do not email before value proposition and metadata are clean |

## Standing principles

1. **Root cause first.** Fix the implementation problem before changing tests.
2. **Explicit consent.** External submission must be opt-in, redacted, and private by default.
3. **No silent collection.** No raw logs, prompts, file contents, or secrets.
4. **Git as source of truth.** Markdown/JSON first; databases and dashboards are derived surfaces.
5. **Small PRs win.** One bounded change with a test beats broad rewrites.
6. **No DCO, no merge.** DCO is a release-safety gate, not paperwork.
7. **Evidence over hype.** Every milestone needs a command, page, check, issue, or release artifact.

## Contribution focus

Good next contributions:

- Intake endpoint tests and redaction fixtures
- Classifier routing fixtures
- Demand board states and empty/error UI
- High-signal lessons from real failures with verification commands
- MCP tool description and runtime-scan evidence
- Small docs fixes that reduce newcomer friction

Avoid for now:

- More badge-only PRs
- New public listing submissions without product evidence
- Auto-publication of private feedback
- Large hub rewrites not needed for the intake loop
