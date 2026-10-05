"""
main.py — Interactive Terminal Demo

Run this to chat with the Smart DevOps Agent in your terminal.
Demonstrates all 9 tasks: state, reasoning, tools, MCP, hooks,
HITL, compaction, telemetry.

Usage:
    python main.py
    python main.py --no-mcp      # skip MCP server discovery
"""

import sys
import uuid
from langchain_core.messages import HumanMessage
from langgraph.types import Command

from agent.graph import create_graph
from telemetry.tracing import create_langfuse_handler


def print_banner():
    print("\n" + "=" * 60)
    print("  🤖  Smart DevOps Assistant")
    print("  Covers: State · Reasoning · Tools · MCP · Hooks")
    print("          HITL · Compaction · Telemetry")
    print("=" * 60)
    print("\nTry these commands:")
    print("  • Check server health for prod-1")
    print("  • Search error logs for database timeout")
    print("  • Create a critical ticket for API outage")
    print("  • Get summary of incident INC-001")
    print("  • Get service status for production")
    print("  • Deploy auth-service version 2.1.0  (triggers HITL)")
    print("\nType 'quit' to exit.\n")


def main():
    use_mcp = "--no-mcp" not in sys.argv

    print_banner()

    # ── Build graph ──────────────────────────────────────────────────────
    print("🔧 Building agent graph...")
    graph, _ = create_graph(use_mcp=use_mcp)

    # ── Langfuse telemetry ───────────────────────────────────────────────
    langfuse = create_langfuse_handler()
    callbacks = [langfuse] if langfuse else []

    # ── Session config (for checkpointing) ───────────────────────────────
    thread_id = str(uuid.uuid4())[:8]
    config = {
        "configurable": {"thread_id": thread_id},
        "callbacks": callbacks,
    }
    print(f"📌 Session: {thread_id}\n")

    # ── Chat loop ────────────────────────────────────────────────────────
    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye! 👋")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("Goodbye! 👋")
            break

        # Invoke the graph
        result = graph.invoke(
            {"messages": [HumanMessage(content=user_input)]},
            config=config,
        )

        # ── Check for HITL interrupt ─────────────────────────────────────
        state = graph.get_state(config)
        while state.next:  # graph is paused (interrupt)
            # Show interrupt info
            for task in state.tasks:
                if hasattr(task, "interrupts"):
                    for intr in task.interrupts:
                        val = intr.value
                        print(f"\n⚠️  {val.get('message', 'Approval required!')}")
                        if "tool" in val:
                            print(f"   Tool: {val['tool']}")
                        if "arguments" in val:
                            print(f"   Args: {val['arguments']}")

            # Ask for human decision
            approval = input("   Your decision (approve / reject): ").strip()
            if not approval:
                approval = "reject"

            # Resume graph
            result = graph.invoke(
                Command(resume=approval),
                config=config,
            )
            state = graph.get_state(config)

        # ── Print the final response ─────────────────────────────────────
        last_msg = result["messages"][-1]
        print(f"\n🤖 Agent: {last_msg.content}\n")


if __name__ == "__main__":
    main()
