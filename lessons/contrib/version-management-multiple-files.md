{
  "title": "Version Management Across Multiple Files",
  "domain": "devops",
  "tags": ["version", "release", "changelog", "documentation"],
  "status": "published",
  "source": "agent_experience",
  "created": "2026-07-02"
}
---

## Problem

Version number appears in multiple files that need to be updated together:

- `pyproject.toml` — Python package version
- `CHANGELOG.md` — Release notes
- `README.md` — Badge and metrics
- `README.zh-CN.md` — Chinese README
- `docs/index.html` — Frontend version badge
- `docs/integrations/README.md` — Integration docs
- `scripts/mcp_server.py` — MCP server version

Missing any file causes inconsistent version display.

## Root Cause

No single source of truth for version number. Each file hardcodes the version independently, requiring manual synchronization.

## Fix

### Checklist for Version Bump

1. **pyproject.toml**
   ```toml
   version = "X.Y.Z"
   ```

2. **CHANGELOG.md**
   ```markdown
   ## vX.Y.Z — YYYY-MM-DD
   
   ### Highlights
   - Feature 1
   - Feature 2
   
   ### Fixes
   - Fix 1
   - Fix 2
   ```

3. **README.md**
   ```markdown
   <a href="..."><img src="https://img.shields.io/badge/lessons-NNN+-blue" /></a>
   ```
   Update: lesson count, node count, metrics table

4. **README.zh-CN.md**
   - Same updates as README.md

5. **docs/index.html**
   ```html
   <span>vX.Y.Z</span>
   <span>YYYY-MM-DD</span>
   <div>NNN</div>  <!-- lesson count -->
   ```

6. **docs/integrations/README.md**
   ```markdown
   Search NNN+ lessons directly from your workflow.
   ```

7. **scripts/mcp_server.py**
   ```python
   "version": "X.Y.Z"
   ```

### Verification

```bash
# Check all version references
grep -rn "old.version" --include="*.md" --include="*.py" --include="*.toml" --include="*.html"

# Verify no stale references remain
grep -rn "149\|185\|192" README.md README.zh-CN.md docs/index.html
```

## Notes

- Consider using `bump2version` or similar tool for automated version bumping
- Keep lesson count in sync with actual `lessons/` directory
- Update frontend stats when lesson count changes significantly
