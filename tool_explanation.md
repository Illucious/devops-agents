# 🛠️ How the Tools Work (Under the Hood)

Right now, **all the tools are returning simulated (dummy) data**. Since this is an assessment designed to test your ability to build the *architecture* (the state machine, MCP, hooks, HITL, telemetry), the actual infrastructure interactions are mocked. This allows the agent to run instantly without requiring a real AWS/Kubernetes environment or third-party API keys.

Here is exactly how the underlying machinery works for each set of tools:

## 1. The Local Tools (Simulated Python functions)
**Location:** `agent/tools.py`

When the LLM decides an action is needed, it outputs a JSON-RPC tool call. The LangGraph `ToolNode` intercepts this, parses the JSON arguments, and routes the execution to one of these Python functions:

*   **`check_server_health`**: Uses Python's `random` library to generate fake CPU (10-95%) and Memory usage on the fly. If it rolls >90%, it flags the server as "critical", otherwise it reports "healthy".
*   **`search_logs`**: Uses a hardcoded list of 6-7 fake log templates (e.g., *"Database connection pool exhausted"*). The function filters these templates based on the `severity` the LLM requested, generates mock timestamps, and returns the formatted text.
*   **`run_deployment`**: Doesn't actually execute a real deployment pipeline. It returns a hardcoded success string with the current datetime, but **only** after it successfully passes through the HITL (Human-in-the-Loop) node in `hitl.py` where a human must explicitly approve it.

## 2. The MCP Tools (Dynamic via stdio)
**Location:** `mcp_server/server.py`

These represent external enterprise systems (like Jira or Datadog) decoupled from the agent's core codebase. The agent dynamically discovers them at startup.
*   **`create_incident_ticket`**: Generates a random ticket ID like `INC-4812`, accepts the LLM's title and description, and returns a JSON payload indicating the ticket was successfully opened.
*   **`get_incident_summary` & `get_service_status`**: Return static, hardcoded JSON dictionaries simulating the exact payload a real ticketing system or service mesh API would return.

## 3. The Lifecycle Hooks (Production Guardrails)
**Location:** `agent/hooks.py`

This is the most critical part for production safety. These hooks wrap the tool execution:
*   **Pre-hook (Validation):** Before `search_logs` executes, the hook intercepts the arguments. If it detects a SQL injection attempt (e.g., `DROP TABLE users`), it **blocks** the tool from running and returns a 400 error back to the LLM. The LLM processes this error, realizes it violated safety protocols, and self-corrects its query.
*   **Post-hook (Transformation):** After a tool runs, the post-hook intercepts the output before handing it back to the LLM. For log searches, it uses regex to replace sensitive IP addresses with `[REDACTED_IP]`. For ticket creation, it appends a tamper-proof `[AUDIT]` timestamp to the result.

---

### 💡 Interview Talking Point
If the interviewer asks about the mock data, you can answer with:

> *"The current tools use mocked data to demonstrate the orchestration and routing logic. The Python functions are built as clean abstraction layers — to move this to production, I would simply replace the `random` logic in `check_server_health` with a `boto3` call to AWS CloudWatch, and replace the log search with a real API request to Datadog or Splunk. The underlying LangGraph architecture, the hooks, and the MCP decoupling wouldn't need to change at all."*
