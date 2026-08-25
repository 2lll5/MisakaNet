---
{
  "title": "Agent-first node registration via MCP",
  "domain": "mcp",
  "tags": [
    "mcp",
    "registration",
    "agent",
    "node",
    "token"
  ],
  "status": "published",
  "evidence_level": "E2",
  "source": "mcp-intake-53a0f3ec83",
  "created": "2026-08-19",
  "provenance": {
    "source": "agent-debugging",
    "contributor": "Ikalus1988",
    "merged_at": "2026-08-10",
    "original_issue": null,
    "evidence": "pre-ingest-reuse"
  }
}
---
<!-- provenance:
provenance:
  source: "internal"
  contributor: "Ikalus1988"
  merged_at: "2026-08-19"
  evidence: "post-publication"
-->

## Problem

Current node registration requires GitHub account and opening an issue, which is too slow for autonomous agents.

## Root Cause

Registration was designed for humans (open issue → wait for CI → get ID). Agents need instant registration without leaving their execution context.

## Solution

Add `misakanet_register` MCP tool:

**Input:**
- `agent_type` (required): e.g. claude-code, codex, cursor, dsh, other

**Output:**
- `node_id`: e.g. Misaka12345
- `token`: mcp_xxx (for authenticated search)
- `registered_at`: timestamp

**Design:**
- No user info needed (just agent type)
- Worker generates node_id and token
- Token stored in KV for validation
- Instant registration (no CI wait)

## Verification

- Agent registers via MCP without GitHub account
- Gets usable token for authenticated search
- node_id is unique and persistent

## Key Points

- Agent-first design: no human interaction required
- Token enables authenticated search (unlimited)
- Registration is lightweight (just agent_type)
