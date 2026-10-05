"""
Task 6: Human-in-the-Loop (HITL) Routing

High-stakes actions (like deployments) require manual approval.
The graph pauses via LangGraph's `interrupt()`, persists state,
and resumes only after the human types "approve" or "reject".
"""

from langgraph.types import interrupt
from langchain_core.messages import ToolMessage


# ── High-stakes tools that require approval ──────────────────────────────────
TOOLS_REQUIRING_APPROVAL = {"run_deployment"}


def needs_human_approval(tool_name: str) -> bool:
    """Check whether a tool call requires human-in-the-loop approval."""
    return tool_name in TOOLS_REQUIRING_APPROVAL


def hitl_node(state: dict) -> dict:
    """Pause execution and wait for human approval.

    Uses LangGraph's interrupt() to freeze the graph.
    The caller resumes with:
        graph.invoke(Command(resume="approve"), config)
    or
        graph.invoke(Command(resume="reject"), config)
    """
    last_message = state["messages"][-1]

    if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
        return {"approval_status": "approved"}

    tool_call = last_message.tool_calls[0]

    # ── Pause here — graph freezes until human responds ──────────────────
    human_response = interrupt(
        {
            "message": "🚨 High-stakes action requires approval!",
            "tool": tool_call["name"],
            "arguments": tool_call["args"],
            "instructions": "Reply with 'approve' to proceed or 'reject' to cancel.",
        }
    )

    # ── Resume path ──────────────────────────────────────────────────────
    if isinstance(human_response, str) and human_response.strip().lower() == "approve":
        return {
            "approval_status": "approved",
            "needs_approval": False,
        }
    else:
        # Rejection: send an error ToolMessage so the LLM knows
        rejection_msg = ToolMessage(
            content=(
                f"❌ Deployment REJECTED by human operator. "
                f"Reason: {human_response}. "
                f"Do NOT retry this deployment unless the user explicitly asks."
            ),
            tool_call_id=tool_call["id"],
        )
        return {
            "messages": [rejection_msg],
            "approval_status": "rejected",
            "needs_approval": False,
        }
