---
{
  "title": "MCP intake: agents submit failures without GitHub account",
  "domain": "mcp",
  "tags": ["mcp", "intake", "agent", "contribution", "no-auth"],
  "status": "published",
  "evidence_level": "E2",
  "source": "mcp-intake-315447a36f",
  "created": "2026-08-19"
}
---

## Problem

Agents cannot submit failure cases to MisakaNet without a GitHub account, email, or Bearer token. This limits the contribution funnel for autonomous agents.

## Root Cause

The only way to contribute was through GitHub PRs or email, both requiring accounts. Agents running remotely have no way to report failures they encounter.

## Solution

Add `misakanet_submit_intake` MCP tool:



**Expected Output:**
```
OK
```
## Key Points

- Intake is always free (no registration required)
- Spam guard prevents abuse
- Maintainer review required before lesson creation
