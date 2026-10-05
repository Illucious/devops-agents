"""
Task 8: Continuous Telemetry (Observability)

Integrates the Langfuse Python SDK to trace every LLM call,
tool execution, latency, and token count.

Usage:
    handler = create_langfuse_handler()
    graph.invoke(input, config={"callbacks": [handler]})

Then inspect traces at https://cloud.langfuse.com
"""

import os
from dotenv import load_dotenv

load_dotenv()


def create_langfuse_handler():
    """Create a Langfuse CallbackHandler for LangGraph tracing.

    Returns None (with a warning) if keys are not configured,
    so the agent can still run without telemetry in dev mode.
    """
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

    if not public_key or not secret_key:
        print(
            "⚠️  Langfuse keys not set — telemetry disabled. "
            "Set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY in .env"
        )
        return None

    try:
        from langfuse.langchain import CallbackHandler

        handler = CallbackHandler()
        print(f"✅ Langfuse telemetry enabled → {host}")
        return handler
    except ImportError:
        print("⚠️  langfuse package not installed — telemetry disabled.")
        return None
