"""
Task 7: Context Compaction & Checkpointing

If the agent takes many steps, the token window fills up and crashes.
This module:
  1. Detects when messages > threshold.
  2. Summarizes the oldest messages into a single paragraph.
  3. Replaces them using LangGraph's RemoveMessage pattern.

Checkpointing (SqliteSaver) is wired in graph.py so the agent
can survive server reboots.
"""

from langchain_core.messages import SystemMessage, RemoveMessage, HumanMessage
from agent.reasoning import create_llm

# ── Config ───────────────────────────────────────────────────────────────────
COMPACTION_THRESHOLD = 10   # trigger when message count exceeds this
MESSAGES_TO_SUMMARIZE = 8   # how many of the oldest messages to compress


def should_compact(state: dict) -> str:
    """Conditional edge: decide whether compaction is needed.

    Returns:
        'compact' or 'continue'
    """
    if len(state["messages"]) > COMPACTION_THRESHOLD:
        return "compact"
    return "continue"


def compact_node(state: dict) -> dict:
    """Summarize the oldest messages into one paragraph, delete originals.

    Uses an offline LLM call (same model) to produce the summary.
    The old messages are removed via RemoveMessage and replaced with
    a single SystemMessage containing the summary.
    """
    messages = state["messages"]
    to_summarize = messages[:MESSAGES_TO_SUMMARIZE]
    keep = messages[MESSAGES_TO_SUMMARIZE:]

    # ── Build a summary via LLM ──────────────────────────────────────────
    llm = create_llm()
    summary_prompt = (
        "Summarize the following conversation excerpt in ONE concise paragraph. "
        "Focus on: actions taken, tool results, errors encountered, and any "
        "pending tasks. Do NOT lose important details like ticket IDs or "
        "server names.\n\n"
    )
    for msg in to_summarize:
        role = msg.__class__.__name__.replace("Message", "")
        summary_prompt += f"[{role}]: {msg.content}\n"

    summary_response = llm.invoke([HumanMessage(content=summary_prompt)])

    # ── Build the replacement ────────────────────────────────────────────
    # 1. Delete old messages
    delete_msgs = [RemoveMessage(id=m.id) for m in to_summarize]
    # 2. Insert summary as a SystemMessage
    summary_msg = SystemMessage(
        content=f"[CONVERSATION SUMMARY]: {summary_response.content}"
    )

    return {
        "messages": delete_msgs + [summary_msg],
        "summary_count": state.get("summary_count", 0) + 1,
    }
