"""
Agent Graph — Full LangGraph wiring

This is the central module that composes every task:
  Task 1 (State)       → AgentState
  Task 2 (Reasoning)   → reasoning_node
  Task 3 (Tools)       → tool_executor_with_hooks
  Task 4 (MCP)         → MCPToolManager discovery
  Task 5 (Hooks)       → pre/post hooks inside tool executor
  Task 6 (HITL)        → hitl_node + conditional edge
  Task 7 (Compaction)  → compact_node + conditional edge
  Task 8 (Telemetry)   → Langfuse callbacks injected at invoke-time
"""

import os
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import SystemMessage, ToolMessage, AIMessage

from agent.state import AgentState
from agent.reasoning import create_llm, SYSTEM_PROMPT
from agent.tools import LOCAL_TOOLS
from agent.hooks import pre_tool_hook, post_tool_hook
from agent.hitl import hitl_node, needs_human_approval
from agent.compaction import should_compact, compact_node


# ═══════════════════════════════════════════════════════════════════════════
#  BUILD THE GRAPH
# ═══════════════════════════════════════════════════════════════════════════

def create_graph(use_mcp: bool = True):
    """Build and compile the full agent graph.

    Args:
        use_mcp: If True, discover MCP tools at startup. Set False for
                 faster iteration when the MCP server isn't running.

    Returns:
        (compiled_graph, checkpointer)
    """
    # ── 1. Collect all tools ─────────────────────────────────────────────
    all_tools = list(LOCAL_TOOLS)

    if use_mcp:
        try:
            from agent.mcp_client import MCPToolManager

            mcp_server_path = os.path.join(
                os.path.dirname(__file__), "..", "mcp_server", "server.py"
            )
            mcp_manager = MCPToolManager(mcp_server_path)
            mcp_tools = mcp_manager.discover_and_create_tools()
            all_tools.extend(mcp_tools)
            print(f"✅ Loaded {len(mcp_tools)} MCP tools + {len(LOCAL_TOOLS)} local tools")
        except Exception as e:
            print(f"⚠️  MCP discovery failed ({e}), using local tools only")

    # Build a name→tool lookup for the executor
    tool_map = {t.name: t for t in all_tools}

    # ── 2. Create the LLM with tools bound ───────────────────────────────
    llm = create_llm()
    llm_with_tools = llm.bind_tools(all_tools)

    # ── 3. Define nodes ──────────────────────────────────────────────────

    def reasoning_node(state: AgentState) -> dict:
        """Core reasoning: call LLM, get tool-calls or final answer."""
        messages = list(state["messages"])
        # Inject system prompt if missing
        if not messages or not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages
        response = llm_with_tools.invoke(messages)
        return {
            "messages": [response],
            "iteration": state.get("iteration", 0) + 1,
        }

    def tool_executor_with_hooks(state: AgentState) -> dict:
        """Execute tool calls with pre- and post-hooks (Task 3 + Task 5)."""
        last_message = state["messages"][-1]
        results = []

        for tool_call in last_message.tool_calls:
            name = tool_call["name"]
            args = tool_call["args"]

            # ── PRE-HOOK ─────────────────────────────────────────────
            validation = pre_tool_hook(name, args)
            if validation["error"]:
                results.append(
                    ToolMessage(
                        content=(
                            f"Error {validation['status_code']}: "
                            f"{validation['message']}"
                        ),
                        tool_call_id=tool_call["id"],
                        name=name,
                    )
                )
                continue  # skip execution, LLM will self-correct

            # ── EXECUTE ──────────────────────────────────────────────
            tool_fn = tool_map.get(name)
            if tool_fn is None:
                results.append(
                    ToolMessage(
                        content=f"Error 404: Unknown tool '{name}'",
                        tool_call_id=tool_call["id"],
                        name=name,
                    )
                )
                continue

            try:
                raw_result = tool_fn.invoke(args)
            except Exception as exc:
                results.append(
                    ToolMessage(
                        content=f"Error 500: Tool execution failed — {exc}",
                        tool_call_id=tool_call["id"],
                        name=name,
                    )
                )
                continue

            # ── POST-HOOK ────────────────────────────────────────────
            processed = post_tool_hook(name, str(raw_result))

            results.append(
                ToolMessage(
                    content=processed,
                    tool_call_id=tool_call["id"],
                    name=name,
                )
            )

        return {"messages": results}

    # ── 4. Routing functions ─────────────────────────────────────────────

    def route_after_reasoning(state: AgentState) -> str:
        """After LLM responds: end / hitl / tools."""
        last = state["messages"][-1]

        # No tool calls → final answer
        if not isinstance(last, AIMessage) or not getattr(last, "tool_calls", None):
            return "end"

        # Check if ANY tool call requires human approval
        for tc in last.tool_calls:
            if needs_human_approval(tc["name"]):
                return "hitl"

        return "tools"

    def route_after_hitl(state: AgentState) -> str:
        """After human decision: approved → execute, rejected → back to LLM."""
        if state.get("approval_status") == "approved":
            return "execute"
        return "rejected"

    def route_after_tools(state: AgentState) -> str:
        """After tool execution: compact if needed, else loop back."""
        return should_compact(state)

    # ── 5. Wire the graph ────────────────────────────────────────────────
    builder = StateGraph(AgentState)

    # Add nodes
    builder.add_node("reasoning", reasoning_node)
    builder.add_node("tools", tool_executor_with_hooks)
    builder.add_node("hitl", hitl_node)
    builder.add_node("compact", compact_node)

    # Entry point
    builder.set_entry_point("reasoning")

    # Reasoning → {end, hitl, tools}
    builder.add_conditional_edges(
        "reasoning",
        route_after_reasoning,
        {"end": END, "hitl": "hitl", "tools": "tools"},
    )

    # HITL → {execute (tools), rejected (reasoning)}
    builder.add_conditional_edges(
        "hitl",
        route_after_hitl,
        {"execute": "tools", "rejected": "reasoning"},
    )

    # Tools → {compact, continue (reasoning)}
    builder.add_conditional_edges(
        "tools",
        route_after_tools,
        {"compact": "compact", "continue": "reasoning"},
    )

    # Compact → reasoning
    builder.add_edge("compact", "reasoning")

    # ── 6. Compile with checkpointing (Task 7) ──────────────────────────
    checkpointer = MemorySaver()

    graph = builder.compile(
        checkpointer=checkpointer,
        interrupt_before=["hitl"],  # pause BEFORE hitl node for HITL
    )

    return graph, checkpointer
