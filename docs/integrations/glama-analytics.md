# Glama Analytics counting boundary

Date checked: 2026-08-02
MisakaNet version: v2.14.0
Glama listing: https://glama.ai/mcp/servers/Ikalus1988/MisakaNet
Related issue: #764

## Short conclusion

Glama currently shows **0 Glama-routed tool calls** for MisakaNet. Do **not** describe this as "0 usage".

The current public evidence says MisakaNet is listed on Glama, but the Glama server API returns an empty `tools` array for this listing. That means there is no verified Glama-hosted tool endpoint to exercise from this checkout yet. Local stdio usage through Claude Desktop, Cursor, Claude Code, shell, or Docker should be treated as outside the Glama Analytics `Tool Calls` counter unless Glama documents otherwise.

## Evidence collected

### Glama listing API

Command:

```powershell
Invoke-RestMethod -Uri 'https://glama.ai/api/mcp/v1/servers/Ikalus1988/MisakaNet' | ConvertTo-Json -Depth 10
```

Observed key fields on 2026-08-02:

```json
{
  "id": "dr8pugtliz",
  "name": "MisakaNet",
  "namespace": "Ikalus1988",
  "repository": { "url": "https://github.com/Ikalus1988/MisakaNet" },
  "tools": [],
  "url": "https://glama.ai/mcp/servers/dr8pugtliz"
}
```

Interpretation: the Glama listing exists, but Glama does not currently expose discovered tool metadata for MisakaNet through this API response.

### Local MCP stdio smoke

Local stdio calls are working independently of Glama:

- `initialize` returned server name `misakanet`.
- `tools/list` returned `misakanet_search`, `misakanet_get_lesson`, `misakanet_submit_usage`, and `misakanet_usage_status`.
- `tools/call` for `misakanet_search` with query `database locked` returned SAG-Lite results.
- `tools/call` for `misakanet_usage_status` returned quota status for `anon:mcp-default`.

This proves the MCP server works locally, but it does not prove Glama Analytics increments for those local calls.

## Required wording

Use:

> Glama currently shows 0 Glama-routed tool calls; local stdio usage is not counted or not yet confirmed by that metric.

Avoid:

> MisakaNet has 0 usage.

## Follow-up

1. Ask Glama or check Glama maintainer docs for whether a hosted/gateway endpoint can be enabled for this listing.
2. If a hosted/gateway endpoint appears, run one `tools/call` through that endpoint and re-check analytics after 10-30 minutes.
3. Keep first-call conversion work focused on copy-paste setup until a hosted Glama path is confirmed.
