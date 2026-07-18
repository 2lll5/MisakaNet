#!/usr/bin/env python3
"""MisakaNet MCP Server — thin adapter for Claude Code, Cursor, Continue, etc.

Exposes 3 tools:
  misakanet.search(query, domain?, top?)
  misakanet.get_lesson(path_or_id)
  misakanet.submit_usage(lesson_id, tool, outcome)

Usage:
    # As MCP server (stdio transport)
    python3 scripts/mcp_server.py

    # In Claude Code settings.json:
    {
      "mcpServers": {
        "misakanet": {
          "command": "python3",
          "args": ["C:/Users/hp/MisakaNet/scripts/mcp_server.py"]
        }
      }
    }
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

# Import SAG-Lite search
try:
    from scripts.build_sag_index import search as sag_search
    SAG_DB = REPO_ROOT / "data" / "sag.db"
    HAS_SAG = SAG_DB.exists()
except ImportError:
    HAS_SAG = False

# Import BM25 search fallback
try:
    from misakanet.search.engine import MisakaNetSearchEngine
    HAS_BM25 = True
except ImportError:
    HAS_BM25 = False


def handle_search(args: dict) -> dict:
    """Search MisakaNet lessons."""
    query = args.get("query", "")
    domain = args.get("domain")
    top = args.get("top", 5)

    if not query:
        return {"error": "query is required"}

    if HAS_SAG:
        results = sag_search(SAG_DB, query, domain=domain, top=top)
        return {"results": results, "source": "sag-lite"}
    elif HAS_BM25:
        engine = MisakaNetSearchEngine()
        results = engine.search(query, top=top)
        return {"results": results, "source": "bm25"}
    else:
        return {"error": "No search engine available. Run: python3 scripts/build_sag_index.py"}


def handle_get_lesson(args: dict) -> dict:
    """Get a lesson by path or ID."""
    path_or_id = args.get("path", args.get("id", ""))
    if not path_or_id:
        return {"error": "path or id is required"}

    # Try direct path
    lesson_path = REPO_ROOT / path_or_id
    if not lesson_path.exists():
        # Try searching by ID in lessons/
        for subdir in ["core", "contrib"]:
            candidate = REPO_ROOT / "lessons" / subdir / f"{path_or_id}.md"
            if candidate.exists():
                lesson_path = candidate
                break

    if not lesson_path.exists():
        return {"error": f"Lesson not found: {path_or_id}"}

    content = lesson_path.read_text(encoding="utf-8", errors="replace")
    return {
        "path": str(lesson_path.relative_to(REPO_ROOT)),
        "content": content[:5000],  # Truncate for MCP context window
    }


def handle_submit_usage(args: dict) -> dict:
    """Submit a usage report (placeholder — creates GitHub Issue via API)."""
    lesson_id = args.get("lesson_id", "")
    tool = args.get("tool", "unknown")
    outcome = args.get("outcome", "unknown")

    if not lesson_id:
        return {"error": "lesson_id is required"}

    # For now, just log locally
    report = {
        "lesson_id": lesson_id,
        "tool": tool,
        "outcome": outcome,
        "status": "logged",
    }

    # TODO: POST to /api/usage or create GitHub Issue
    return report


# ── MCP Resources ──
RESOURCES = [
    {
        "uri": "misaka://lessons/index",
        "name": "Lessons Index",
        "description": "Browse all published lessons (core + contrib) with metadata",
        "mimeType": "application/json",
    },
    {
        "uri": "misaka://protocol/overview",
        "name": "Protocol Overview",
        "description": "Swarm Knowledge Protocol configuration (trust tiers, rings, scoring)",
        "mimeType": "application/json",
    },
    {
        "uri": "misaka://docs/readme",
        "name": "README",
        "description": "Project overview, quickstart, and integration guide",
        "mimeType": "text/markdown",
    },
    {
        "uri": "misaka://docs/faq",
        "name": "Troubleshooting FAQ",
        "description": "Common issues and solutions for MisakaNet users",
        "mimeType": "text/markdown",
    },
    {
        "uri": "misaka://docs/changelog",
        "name": "Changelog",
        "description": "Latest release notes and version history",
        "mimeType": "text/markdown",
    },
]


def handle_resources_list() -> list:
    """Return available resources."""
    return RESOURCES


def handle_resources_read(uri: str) -> dict:
    """Read a resource by URI."""
    if uri == "misaka://lessons/index":
        lessons = []
        for subdir in ["core", "contrib"]:
            d = REPO_ROOT / "lessons" / subdir
            if d.exists():
                for f in sorted(d.glob("*.md")):
                    lessons.append({
                        "id": f.stem,
                        "path": str(f.relative_to(REPO_ROOT)),
                        "category": subdir,
                    })
        return {"lessons": lessons, "count": len(lessons)}

    elif uri == "misaka://protocol/overview":
        p = REPO_ROOT / "misaka-protocol.json"
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
        return {"error": "misaka-protocol.json not found"}

    elif uri == "misaka://docs/readme":
        p = REPO_ROOT / "README.md"
        if p.exists():
            return {"content": p.read_text(encoding="utf-8", errors="replace")[:8000]}
        return {"error": "README.md not found"}

    elif uri == "misaka://docs/faq":
        p = REPO_ROOT / "docs" / "troubleshooting.md"
        if p.exists():
            return {"content": p.read_text(encoding="utf-8", errors="replace")[:8000]}
        return {"error": "troubleshooting.md not found"}

    elif uri == "misaka://docs/changelog":
        p = REPO_ROOT / "STATUS.md"
        if p.exists():
            return {"content": p.read_text(encoding="utf-8", errors="replace")[:4000]}
        return {"error": "STATUS.md not found"}

    return {"error": f"Unknown resource: {uri}"}


# ── MCP Prompts ──
PROMPTS = [
    {
        "name": "search_lesson",
        "title": "Search Lessons",
        "description": "Search MisakaNet for lessons matching an error or topic",
        "arguments": [
            {"name": "query", "description": "Error message or topic to search for", "required": True},
            {"name": "domain", "description": "Optional domain filter (devops, python, rag, etc.)", "required": False},
        ],
    },
    {
        "name": "triage_failure",
        "title": "Triage Failure",
        "description": "Structured failure triage — find root cause and matching rescue cards",
        "arguments": [
            {"name": "error", "description": "The error message or stack trace", "required": True},
            {"name": "context", "description": "What were you doing when the error occurred", "required": False},
        ],
    },
    {
        "name": "release_audit",
        "title": "Release Audit",
        "description": "Check release readiness against MisakaNet quality gates",
        "arguments": [
            {"name": "version", "description": "Version to audit (e.g., v2.12.0)", "required": True},
        ],
    },
]


def handle_prompts_get(name: str, arguments: dict) -> dict:
    """Return a prompt with arguments filled in."""
    if name == "search_lesson":
        query = arguments.get("query", "")
        domain = arguments.get("domain", "")
        domain_hint = f" in the '{domain}' domain" if domain else ""
        return {
            "description": f"Search for lessons about: {query}",
            "messages": [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": (
                            f"Search MisakaNet lessons for solutions to: \"{query}\"{domain_hint}.\n\n"
                            f"Use the misakanet_search tool with query=\"{query}\""
                            + (f" and domain=\"{domain}\"" if domain else "")
                            + ".\n\nReport the top 3 matches with their relevance score and actionable summary."
                        ),
                    },
                }
            ],
        }

    elif name == "triage_failure":
        error = arguments.get("error", "")
        context = arguments.get("context", "unknown context")
        return {
            "description": f"Triage failure: {error[:80]}",
            "messages": [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": (
                            f"I encountered this error while {context}:\n\n"
                            f"```\n{error}\n```\n\n"
                            "Please:\n"
                            "1. Search MisakaNet for matching lessons using misakanet_search\n"
                            "2. If a rescue card exists, apply its fix\n"
                            "3. If no match, suggest the root cause and next diagnostic steps"
                        ),
                    },
                }
            ],
        }

    elif name == "release_audit":
        version = arguments.get("version", "latest")
        return {
            "description": f"Audit release {version}",
            "messages": [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": (
                            f"Audit MisakaNet release {version} for readiness.\n\n"
                            "Check:\n"
                            "1. Read misaka://docs/changelog for this version's changes\n"
                            "2. Verify all lessons in misaka://lessons/index have valid frontmatter\n"
                            "3. Check protocol version matches in misaka://protocol/overview\n"
                            "4. Report any gaps or blockers for release"
                        ),
                    },
                }
            ],
        }

    return {"error": f"Unknown prompt: {name}"}


# ── MCP Tools ──
TOOLS = [
    {
        "name": "misakanet_search",
        "description": "Search MisakaNet lessons for solutions to errors, bugs, and technical problems.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query (error message, keyword, or topic)"},
                "domain": {"type": "string", "description": "Filter by domain (devops, python, network, feishu, rag, etc.)"},
                "top": {"type": "integer", "description": "Number of results (default 5)"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "misakanet_get_lesson",
        "description": "Get the full content of a specific lesson by path or ID.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Lesson path (e.g., lessons/core/auto-merge-ci-pipeline.md)"},
                "id": {"type": "string", "description": "Lesson ID (filename without .md)"},
            },
        },
    },
    {
        "name": "misakanet_submit_usage",
        "description": "[Experimental] Report that a lesson was used to solve a problem. Currently logs locally only.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "lesson_id": {"type": "string", "description": "ID of the lesson that helped"},
                "tool": {"type": "string", "description": "Your tool name (e.g., claude-code, cursor, aider)"},
                "outcome": {"type": "string", "description": "Outcome: solved, partial, not-helpful"},
            },
            "required": ["lesson_id"],
        },
    },
]


def handle_request(request: dict) -> dict:
    """Handle a JSON-RPC request."""
    method = request.get("method", "")
    params = request.get("params", {})
    req_id = request.get("id")

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2025-06-18",
                "capabilities": {
                    "tools": {},
                    "resources": {},
                    "prompts": {},
                },
                "serverInfo": {
                    "name": "misakanet",
                    "version": "2.12.0",
                },
            },
        }

    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": TOOLS},
        }

    elif method == "tools/call":
        tool_name = params.get("name", "")
        tool_args = params.get("arguments", {})

        handlers = {
            "misakanet_search": handle_search,
            "misakanet_get_lesson": handle_get_lesson,
            "misakanet_submit_usage": handle_submit_usage,
        }

        handler = handlers.get(tool_name)
        if not handler:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"},
            }

        result = handler(tool_args)
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}],
            },
        }

    elif method == "notifications/initialized":
        return None

    # ── Resources ──
    elif method == "resources/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"resources": handle_resources_list()},
        }

    elif method == "resources/read":
        uri = params.get("uri", "")
        content = handle_resources_read(uri)
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "contents": [
                    {"uri": uri, "mimeType": "application/json", "text": json.dumps(content, ensure_ascii=False)}
                ]
            },
        }

    # ── Prompts ──
    elif method == "prompts/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"prompts": PROMPTS},
        }

    elif method == "prompts/get":
        name = params.get("name", "")
        arguments = params.get("arguments", {})
        result = handle_prompts_get(name, arguments)
        if "error" in result:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32602, "message": result["error"]},
            }
        return {"jsonrpc": "2.0", "id": req_id, "result": result}

    else:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Unknown method: {method}"},
        }


def main():
    """MCP stdio server loop."""
    # Write to stderr for debug (stdout is for MCP protocol)
    sys.stderr.write("MisakaNet MCP Server started\n")
    sys.stderr.write(f"SAG-Lite: {'available' if HAS_SAG else 'not available (run build_sag_index.py)'}\n")
    sys.stderr.write(f"BM25: {'available' if HAS_BM25 else 'not available'}\n")

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            continue

        response = handle_request(request)
        if response:
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
