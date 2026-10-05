"""
Task 2: Build the Reasoning Node (The Engine)

The core node that decides what to do next.
It does NOT execute actions — it only outputs tool-call requests
(as JSON in the AIMessage.tool_calls) or a final text answer.
"""

import os
from langchain_groq import ChatGroq
from dotenv import load_dotenv

load_dotenv()

# ── System Prompt ────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are a **Smart DevOps Assistant**. You help engineers monitor, debug, \
and manage their infrastructure.

## Capabilities
- Check server health metrics (CPU, memory, disk)
- Search application logs by keyword and severity
- Create incident tickets for tracking issues
- Get detailed summaries of past incidents
- Check service status across environments (production / staging / dev)
- Run deployments (⚠️ requires human approval first)

## Guidelines
1. When asked to check health, use `check_server_health`.
2. For log searches, use `search_logs` with the right severity filter.
3. For incident tickets, always ask the user for title, description, and \
   priority if not provided.
4. For deployments, ALWAYS warn the user that this requires human approval.
5. If a tool call returns an error (e.g. 400), read the error message, \
   fix your parameters, and retry.
6. Provide concise, actionable insights based on the data you retrieve.
7. When multiple steps are needed, explain your plan first.
"""


def create_llm():
    """Create the Groq LLM instance (unbound — tools are bound in graph.py)."""
    return ChatGroq(
        model="qwen/qwen3.8-27b",
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=0.1,
        max_tokens=4096,
    )
