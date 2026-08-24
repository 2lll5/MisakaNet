"""Submit usage and intake handlers for MisakaNet MCP server."""
from __future__ import annotations


def handle_submit_usage(args: dict) -> dict:
    """Submit a usage report (placeholder — creates GitHub Issue via API)."""
    lesson_id = args.get("lesson_id", "")
    tool = args.get("tool", "unknown")
    outcome = args.get("outcome", "unknown")

    if not lesson_id:
        return {
            "error": "lesson_id is required",
            "guidance": (
                "Provide the lesson ID"
                " (e.g. 'auto-merge-ci-pipeline')."
                " Use misakanet_search to discover lesson IDs by topic."
            ),
            "voice": "failure-warning",
        }

    # For now, just log locally
    report = {
        "lesson_id": lesson_id,
        "tool": tool,
        "outcome": outcome,
        "status": "logged",
        "voice": "pair-success",
    }

    # TODO: POST to /api/usage or create GitHub Issue
    return report


def handle_submit_intake(args: dict) -> dict:
    """Submit a failure-case intake via the contribution queue."""
    from scripts.contribution_queue import submit_contribution

    kind = args.get("kind", "missing_lesson")
    problem = args.get("problem", "")
    error = args.get("error", "")
    what_tried = args.get("what_tried", "")
    fix = args.get("fix", "")
    verification = args.get("verification", "")
    matched_lesson_id = args.get("matched_lesson_id", "")
    source = args.get("source", "other")

    if not problem:
        return {
            "error": "problem is required",
            "hint": "Describe the failure or gap you encountered.",
        }

    # Build message from available fields
    parts = [f"Kind: {kind}"]
    if error:
        parts.append(f"Error: {error}")
    if what_tried:
        parts.append(f"Tried: {what_tried}")
    if fix:
        parts.append(f"Fix: {fix}")
    if verification:
        parts.append(f"Verification: {verification}")
    message = "\n".join(parts)

    result = submit_contribution(
        contrib_type="intake",
        user="mcp-agent",
        title=problem[:200],
        message=message,
        problem=problem,
        fix=fix,
        verification=verification,
        source=source,
        lesson_id=matched_lesson_id,
    )

    if "error" in result:
        return {
            "submitted": False,
            "error": result["error"],
            "message": result.get("message", ""),
            "existing_id": result.get("existing_id", ""),
        }

    return {
        "submitted": True,
        "intake_id": result["id"],
        "status": result["status"],
        "redactions_applied": result.get("redactions_applied", 0),
        "quality_score": result.get("quality_score", 0),
        "receipt": (
            f"Keep this ID ({result['id']});"
            " no account or email is required."
        ),
    }
