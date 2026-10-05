"""
Task 9b: FastAPI Deployment Endpoint

Wraps the LangGraph agent in a POST /webhook endpoint.
Supports both single-turn and multi-turn (with HITL approval) requests.

Usage:
    uvicorn app:app --host 0.0.0.0 --port 7860
"""

import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from langchain_core.messages import HumanMessage
from langgraph.types import Command

from agent.graph import create_graph
from telemetry.tracing import create_langfuse_handler


# ── Globals ──────────────────────────────────────────────────────────────────
graph = None
langfuse_handler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Build the agent graph once at startup."""
    global graph, langfuse_handler
    print("🚀 Starting Smart DevOps Agent...")
    graph, _ = create_graph(use_mcp=True)
    langfuse_handler = create_langfuse_handler()
    print("✅ Agent ready!")
    yield
    print("👋 Shutting down.")


app = FastAPI(
    title="Smart DevOps Agent",
    description="AI-powered DevOps assistant with tools, HITL, and MCP",
    version="1.0.0",
    lifespan=lifespan,
)


# ── Request / Response Models ────────────────────────────────────────────────

class WebhookRequest(BaseModel):
    message: str
    thread_id: str | None = None


class ApprovalRequest(BaseModel):
    thread_id: str
    decision: str  # "approve" or "reject"


class WebhookResponse(BaseModel):
    response: str
    thread_id: str
    needs_approval: bool = False
    approval_details: dict | None = None


# ── Endpoints ────────────────────────────────────────────────────────────────

@app.post("/webhook", response_model=WebhookResponse)
async def webhook(request: WebhookRequest):
    """Send a message to the DevOps agent."""
    if graph is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    thread_id = request.thread_id or str(uuid.uuid4())[:8]
    callbacks = [langfuse_handler] if langfuse_handler else []
    config = {
        "configurable": {"thread_id": thread_id},
        "callbacks": callbacks,
    }

    result = graph.invoke(
        {"messages": [HumanMessage(content=request.message)]},
        config=config,
    )

    # Check for HITL interrupt
    state = graph.get_state(config)
    if state.next:
        # Graph is paused — needs human approval
        approval_details = {}
        for task in state.tasks:
            if hasattr(task, "interrupts"):
                for intr in task.interrupts:
                    approval_details = intr.value

        return WebhookResponse(
            response="⚠️ This action requires human approval.",
            thread_id=thread_id,
            needs_approval=True,
            approval_details=approval_details,
        )

    return WebhookResponse(
        response=result["messages"][-1].content,
        thread_id=thread_id,
        needs_approval=False,
    )


@app.post("/approve", response_model=WebhookResponse)
async def approve(request: ApprovalRequest):
    """Approve or reject a pending HITL action."""
    if graph is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    callbacks = [langfuse_handler] if langfuse_handler else []
    config = {
        "configurable": {"thread_id": request.thread_id},
        "callbacks": callbacks,
    }

    result = graph.invoke(
        Command(resume=request.decision),
        config=config,
    )

    return WebhookResponse(
        response=result["messages"][-1].content,
        thread_id=request.thread_id,
        needs_approval=False,
    )


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "agent_loaded": graph is not None}
