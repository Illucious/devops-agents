"""
Task 4: MCP Server (Model Context Protocol)

A standalone MCP server that exposes DevOps tools over stdio transport.
The agent discovers these tools dynamically at startup via MCP's tools/list,
decoupling the agent from the external tool implementations.

Run standalone:  python mcp_server/server.py
"""

import json
import datetime
import random
from mcp.server.mcpserver import MCPServer

# Create the MCP server
mcp = MCPServer("devops-mcp-server")


# ── Tool 1: Create Incident Ticket ──────────────────────────────────────────

@mcp.tool()
def create_incident_ticket(title: str, description: str, priority: str) -> str:
    """Create a new incident ticket in the ticketing system.

    Args:
        title: Short title for the incident ticket.
        description: Detailed description of the incident.
        priority: Priority level — must be 'low', 'medium', 'high', or 'critical'.
    """
    ticket_id = f"INC-{random.randint(1000, 9999)}"
    result = {
        "ticket_id": ticket_id,
        "title": title,
        "description": description,
        "priority": priority,
        "status": "OPEN",
        "created_at": datetime.datetime.now().isoformat(),
        "assigned_to": "on-call-team",
    }
    return json.dumps(result, indent=2)


# ── Tool 2: Get Incident Summary ────────────────────────────────────────────

@mcp.tool()
def get_incident_summary(incident_id: str) -> str:
    """Get a detailed summary of a past incident by its ID.

    Args:
        incident_id: The incident ID (e.g. 'INC-001').
    """
    result = {
        "incident_id": incident_id,
        "title": "Production outage — API gateway",
        "severity": "high",
        "duration": "45 minutes",
        "root_cause": "Memory leak in connection pooling",
        "resolution": "Rolled back to v2.3.1 and patched connection pool config",
        "affected_services": ["api-gateway", "auth-service", "user-service"],
        "timeline": [
            {"time": "14:00", "event": "Alert triggered — 5xx errors spike"},
            {"time": "14:05", "event": "On-call engineer paged"},
            {"time": "14:15", "event": "Root cause identified — memory leak"},
            {"time": "14:30", "event": "Rollback to v2.3.1 initiated"},
            {"time": "14:45", "event": "Service fully restored"},
        ],
    }
    return json.dumps(result, indent=2)


# ── Tool 3: Get Service Status ──────────────────────────────────────────────

@mcp.tool()
def get_service_status(environment: str) -> str:
    """Get the current status of all microservices in an environment.

    Args:
        environment: Target environment — 'production', 'staging', or 'development'.
    """
    services = [
        {"name": "api-gateway",          "status": "running",  "version": "2.4.0", "replicas": 3},
        {"name": "auth-service",         "status": "running",  "version": "1.8.2", "replicas": 2},
        {"name": "user-service",         "status": "degraded", "version": "3.1.0", "replicas": 2},
        {"name": "payment-service",      "status": "running",  "version": "2.0.1", "replicas": 4},
        {"name": "notification-service", "status": "running",  "version": "1.2.0", "replicas": 1},
    ]
    result = {
        "environment": environment,
        "services": services,
        "checked_at": datetime.datetime.now().isoformat(),
    }
    return json.dumps(result, indent=2)


# ── Entrypoint ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run(transport="stdio")
