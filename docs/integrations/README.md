# Integrations

Connect MisakaNet to your AI coding tool. Search 192+ lessons directly from your workflow.

## Available Integrations

| Tool | Status | Setup |
|------|--------|-------|
| **Continue.dev** | ✅ Ready | [Setup Guide](continue/README.md) |
| **Cursor** | Planned | — |
| **Aider** | Planned | — |
| **VS Code** | Planned | — |
| **Cline** | Planned | — |
| **Shell alias** | Ready | See below |

## Quick: Shell Alias

Add to `~/.bashrc` or `~/.zshrc`:

```bash
misaka() {
  local repo="$HOME/MisakaNet"
  if [ ! -d "$repo" ]; then
    git clone https://github.com/Ikalus1988/MisakaNet.git "$repo"
  fi
  cd "$repo" && pip install -q misakanet-core
  python3 search_knowledge.py "$*" --top 5
}
```

Usage: `misaka database locked`

## Python Integration

```python
from misakanet.tools.langchain_tool import MisakaNetSearchTool

tool = MisakaNetSearchTool()
results = tool._run("database locked")
```

## MCP Server (Coming Soon)

MisakaNet will ship as an MCP server for Claude Code, Cursor, and other MCP-compatible tools.

---

*Want to build an integration for your tool? See [bounty #268](https://github.com/Ikalus1988/MisakaNet/issues/268).*
