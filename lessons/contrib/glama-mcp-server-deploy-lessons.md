---
{
  "title": "Glama MCP Server Deployment — 7 Build Failures and Fixes",
  "domain": "devops",
  "tags": ["glama", "mcp", "docker", "uv", "deployment", "ci-cd"],
  "status": "published",
  "source": "agent_experience",
  "created": "2026-07-26",
  "confidence": "0.95"
}
---

## Problem

Deploying a Python MCP server to Glama (MCP registry) requires passing their automated Docker build + introspection test. The build environment uses `debian:trixie-slim` + `uv` (not pip) + Node.js, which has several pitfalls for Python projects.

## Root Cause

Glama's build system:
1. Uses `uv` (astral.sh) to install Python, not system pip
2. System Python is "externally managed" (PEP 668) — blocks `pip install --system`
3. `uv pip install` requires a virtual environment or `--system` flag
4. `--system` fails on Debian's externally-managed Python
5. `uv pip install -e .` requires `pyproject.toml` in the current directory

## 7 Build Failures and Fixes

### Failure 1: `pip: not found`
**Error:** `/bin/sh: 1: pip: not found`
**Cause:** Glama uses `uv` to install Python — no `pip` in PATH
**Fix:** Use `uv pip install` instead of `pip install`

### Failure 2: `No virtual environment found`
**Error:** `No virtual environment found; run uv venv to create an environment`
**Cause:** `uv pip install` without `--system` requires a venv
**Fix:** Create venv first: `uv venv && uv pip install ...`

### Failure 3: `externally managed` (PEP 668)
**Error:** `The interpreter at /usr is externally managed`
**Cause:** `--system` flag targets Debian's system Python, blocked by PEP 668
**Fix:** Don't use `--system` — use venv instead

### Failure 4: `No module named prgenius.__main__`
**Error:** `'prgenius' is a package and cannot be directly executed`
**Cause:** Package cloned but not installed — `python -m prgenius` needs installed package
**Fix:** Add `uv pip install -e .` to install the package itself

### Failure 5: `does not appear to be a Python project`
**Error:** `neither pyproject.toml nor setup.py are present in the directory`
**Cause:** `pyproject.toml` is in subdirectory (`prgenius/`), not root
**Fix:** Use `uv pip install -e ./prgenius` instead of `uv pip install -e .`

### Failure 6: Docker Hub timeout
**Error:** `debian:trixie-slim: failed to resolve source metadata: context deadline exceeded`
**Cause:** Glama's Docker daemon can't pull from Docker Hub (infrastructure issue)
**Fix:** Retry — transient Glama infrastructure issue

### Failure 7: Build cancelled (2h timeout)
**Error:** `The test run did not start within 2 hours; cancelled by maintenance`
**Cause:** Glama build queue overload
**Fix:** Retry during off-peak hours

## Final Working Configuration

```json
{
  "buildSteps": [
    "uv venv && . .venv/bin/activate && uv pip install misakanet-core graphql-core mcp && uv pip install -e ./prgenius"
  ],
  "cmdArguments": [
    "mcp-proxy", "--", ".venv/bin/python", "-m", "prgenius", "mcp", "serve"
  ]
}
```

## Prevention

1. **Always use `uv` commands** in Glama environment — `pip` is not available
2. **Always create venv first** — `uv pip install` requires venv
3. **Use `./subdir` for nested packages** — `pyproject.toml` may not be at root
4. **Use `.venv/bin/python` in CMD** — not system `python`
5. **Test locally first** — simulate the build before submitting to Glama

## Key Takeaway

Glama's build environment is different from standard Docker Python images. The `uv` toolchain requires explicit venv creation and package installation paths. Always verify the full build chain locally before submitting.
