"""
Task 5: Lifecycle Hooks — Pre & Post

Deterministic guardrails for non-deterministic models.

Pre-hook:  Validates tool inputs BEFORE execution.
           Returns a simulated 400 error if validation fails so the LLM
           can self-correct.

Post-hook: Transforms or enriches results AFTER execution.
           (e.g. redact IPs, add audit trail)
"""

import re
import datetime


# ── Pre-Tool Hook ────────────────────────────────────────────────────────────

def pre_tool_hook(tool_name: str, tool_args: dict) -> dict:
    """Validate tool inputs before execution.

    Returns:
        dict with 'error' (bool).  If True, also contains
        'status_code' (int) and 'message' (str).
    """

    # ── search_logs guards ───────────────────────────────────────────────
    if tool_name == "search_logs":
        query = tool_args.get("query", "")
        # Block suspected injection patterns
        dangerous = ["DROP", "DELETE", "TRUNCATE", "ALTER", "EXEC", "--"]
        for kw in dangerous:
            if kw in query.upper():
                return {
                    "error": True,
                    "status_code": 400,
                    "message": (
                        f"Blocked: query contains dangerous keyword '{kw}'. "
                        "Please rephrase your search."
                    ),
                }
        # Validate severity enum
        severity = tool_args.get("severity", "all")
        valid = ["info", "warning", "error", "all"]
        if severity not in valid:
            return {
                "error": True,
                "status_code": 400,
                "message": f"Invalid severity '{severity}'. Must be one of: {valid}",
            }

    # ── create_incident_ticket guards ────────────────────────────────────
    if tool_name == "create_incident_ticket":
        priority = tool_args.get("priority", "")
        valid_priorities = ["low", "medium", "high", "critical"]
        if priority not in valid_priorities:
            return {
                "error": True,
                "status_code": 400,
                "message": (
                    f"Invalid priority '{priority}'. "
                    f"Must be one of: {valid_priorities}"
                ),
            }
        if not tool_args.get("title", "").strip():
            return {
                "error": True,
                "status_code": 400,
                "message": "Ticket title cannot be empty.",
            }
        if not tool_args.get("description", "").strip():
            return {
                "error": True,
                "status_code": 400,
                "message": "Ticket description cannot be empty.",
            }

    # ── run_deployment guards ────────────────────────────────────────────
    if tool_name == "run_deployment":
        if not tool_args.get("service", "").strip():
            return {
                "error": True,
                "status_code": 400,
                "message": "Service name is required for deployment.",
            }
        if not tool_args.get("version", "").strip():
            return {
                "error": True,
                "status_code": 400,
                "message": "Version string is required for deployment.",
            }

    # ── check_server_health guards ───────────────────────────────────────
    if tool_name == "check_server_health":
        if not tool_args.get("server_name", "").strip():
            return {
                "error": True,
                "status_code": 400,
                "message": "Server name cannot be empty.",
            }

    return {"error": False}


# ── Post-Tool Hook ───────────────────────────────────────────────────────────

def post_tool_hook(tool_name: str, result: str) -> str:
    """Transform or enrich tool results after execution.

    Returns:
        The (possibly modified) result string.
    """

    # Redact IP addresses from log output
    if tool_name == "search_logs":
        result = re.sub(
            r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",
            "[REDACTED_IP]",
            result,
        )

    # Add audit trail to ticket creation
    if tool_name == "create_incident_ticket":
        result += (
            f"\n[AUDIT] Ticket created at "
            f"{datetime.datetime.now().isoformat()} by DevOps Agent"
        )

    # Add audit trail to deployments
    if tool_name == "run_deployment":
        result += (
            f"\n[AUDIT] Deployment executed at "
            f"{datetime.datetime.now().isoformat()} by DevOps Agent "
            f"(human-approved)"
        )

    return result
