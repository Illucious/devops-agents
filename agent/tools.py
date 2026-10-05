"""
Task 3: Tool Provisioning & Execution (local tools)

These are the Python functions that the LLM can call.
Each is decorated with @tool to auto-generate the JSON schema
that gets bound to the model.
"""

import random
import datetime
from langchain_core.tools import tool


@tool
def check_server_health(server_name: str) -> str:
    """Check the health status of a server including CPU, memory, and disk usage.

    Args:
        server_name: Name or hostname of the server to check (e.g. 'prod-1').
    """
    cpu = random.randint(10, 95)
    memory = random.randint(20, 90)
    disk = random.randint(30, 85)
    status = (
        "critical" if cpu > 90 or memory > 90
        else "warning" if cpu > 75 or memory > 75
        else "healthy"
    )
    return (
        f"Server: {server_name}\n"
        f"Status: {status}\n"
        f"CPU Usage: {cpu}%\n"
        f"Memory Usage: {memory}%\n"
        f"Disk Usage: {disk}%\n"
        f"Uptime: {random.randint(1, 365)} days\n"
        f"Last Checked: {datetime.datetime.now().isoformat()}"
    )


@tool
def search_logs(query: str, severity: str = "all") -> str:
    """Search application logs by keyword and optional severity filter.

    Args:
        query: Search keyword or phrase to look for in logs.
        severity: Filter by severity level — 'info', 'warning', 'error', or 'all'.
    """
    log_templates = [
        {"severity": "error",   "msg": "Connection timeout on upstream service"},
        {"severity": "error",   "msg": "Database connection pool exhausted"},
        {"severity": "warning", "msg": "High latency detected on /api/users endpoint"},
        {"severity": "warning", "msg": "Disk usage approaching threshold (82%)"},
        {"severity": "info",    "msg": "Service restarted successfully"},
        {"severity": "info",    "msg": "Health check passed"},
        {"severity": "error",   "msg": "Out of memory error in worker process"},
    ]

    # Filter by severity
    if severity != "all":
        log_templates = [l for l in log_templates if l["severity"] == severity]

    # Simulate matching against query
    base_time = datetime.datetime.now() - datetime.timedelta(hours=1)
    lines = []
    for i, log in enumerate(log_templates):
        ts = (base_time + datetime.timedelta(minutes=i * 5)).strftime("%Y-%m-%dT%H:%M:%S")
        lines.append(f"[{ts}] [{log['severity'].upper()}] {log['msg']} (query: {query})")

    if not lines:
        return f"No logs found matching query='{query}' severity='{severity}'"
    return "\n".join(lines)


@tool
def run_deployment(service: str, version: str) -> str:
    """Deploy a specific version of a service to production.
    ⚠️ This is a HIGH-STAKES operation that requires human approval.

    Args:
        service: Name of the micro-service to deploy (e.g. 'auth-service').
        version: Semantic version to deploy (e.g. '2.1.0').
    """
    return (
        f"✅ Deployment Successful!\n"
        f"Service: {service}\n"
        f"Version: {version}\n"
        f"Deploy Time: {datetime.datetime.now().isoformat()}\n"
        f"Status: RUNNING\n"
        f"Health Check: PASSED\n"
        f"Rollback Version: {version.rsplit('.', 1)[0]}.{int(version.rsplit('.', 1)[1]) - 1}"
    )


# Collect all local tools for easy import
LOCAL_TOOLS = [check_server_health, search_logs, run_deployment]
