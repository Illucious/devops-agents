"""
Task 1: Define the State (State Management)

The agent is a state machine. This TypedDict defines the memory object
that passes between every node in the graph.
"""

from typing import TypedDict, Annotated, Literal
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class AgentState(TypedDict):
    """Central state object shared across all graph nodes.

    Fields:
        messages:        Conversation history. Uses the `add_messages` reducer
                         so returning a list of messages *appends* rather than
                         overwrites.
        needs_approval:  Flag set by the router when a high-stakes tool
                         (e.g. run_deployment) is about to be called.
        approval_status: Result of the human-in-the-loop decision.
        hook_status:     Set by the pre-tool hook node — "passed" or "blocked".
        summary_count:   How many times context compaction has been triggered.
        iteration:       Step counter (incremented each reasoning pass).
    """

    messages: Annotated[list[BaseMessage], add_messages]
    needs_approval: bool
    approval_status: Literal["pending", "approved", "rejected"] | None
    hook_status: Literal["passed", "blocked"] | None
    summary_count: int
    iteration: int
