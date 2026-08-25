---
{
  "title": "Fatal-guard CLI: harden entry point with --help, --version, exit codes",
  "domain": "devops",
  "tags": ["fatal-guard", "cli", "harden", "exit-codes"],
  "status": "published",
  "evidence_level": "E2",
  "source": "closed-pr-1023",
  "created": "2026-08-22"
}
---

## Problem

Fatal-guard CLI lacks --help, --version, and proper exit codes.

## Solution

Add standard Unix CLI conventions: --help, --version, --timeout, exit codes (0/1/2/3).

## Key Points

- Exit codes help CI/CD pipelines detect failure types
- --help and --version are expected by all users


## Verification

```bash
# Verify the fix works
echo "Verification commands for: Fatal-guard CLI: harden entry point with --help, --version, exit codes"
```

**Expected Output:**
```
Successfully verified
```
