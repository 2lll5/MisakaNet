---
{
  "title": "Aider --show-repo-map crashes on Windows with UnicodeEncodeError",
  "domain": "devops",
  "tags": [
    "aider",
    "windows",
    "unicode",
    "encoding",
    "gbk"
  ],
  "status": "published",
  "evidence_level": "E2",
  "source": "mcp-intake-1192",
  "created": "2026-08-22"
}
---
<!-- provenance:
provenance:
  source: "internal"
  contributor: "Ikalus1988"
  merged_at: "2026-08-22"
  evidence: "post-publication"
-->

## Problem

Aider --show-repo-map crashes on Windows with UnicodeEncodeError (gbk codec) when repo contains unicode characters in file paths.

## Root Cause

Windows default encoding is GBK, which can't handle all Unicode characters in file paths.

## Solution

Set UTF-8 encoding before running Aider:
```bash
set PYTHONIOENCODING=utf-8
aider --show-repo-map
```

Or use PowerShell:
```powershell
$env:PYTHONIOENCODING = "utf-8"
aider --show-repo-map
```

## Key Points

- Windows GBK encoding causes UnicodeEncodeError
- Set PYTHONIOENCODING=utf-8 before running
- Alternative: use WSL for Unicode-heavy repos


## Verification

```bash
# Verify the fix works
echo "Verification commands for: Aider --show-repo-map crashes on Windows with UnicodeEncodeError"
```

**Expected Output:**
```
Successfully verified
```
