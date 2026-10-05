# 🤖 Smart DevOps Agent

An AI-powered DevOps assistant built with **LangGraph**, **Groq**, and **MCP**.  
Demonstrates all 9 production agent architecture concepts:

| Task | Concept | Implementation |
|------|---------|----------------|
| 1 | **State Management** | `AgentState` TypedDict with `add_messages` reducer |
| 2 | **Reasoning Node** | Groq LLM (llama-3.3-70b) with system prompt + tool binding |
| 3 | **Tool Provisioning** | `@tool`-decorated Python functions with JSON schemas |
| 4 | **MCP (Model Context Protocol)** | FastMCP stdio server + dynamic tool discovery client |
| 5 | **Lifecycle Hooks** | Pre-hook (input validation, injection blocking) + Post-hook (IP redaction, audit trail) |
| 6 | **Human-in-the-Loop** | LangGraph `interrupt()` for deployment approvals |
| 7 | **Context Compaction** | Message summarization when len > 10 + MemorySaver checkpointing |
| 8 | **Telemetry** | Langfuse tracing for latency, tokens, and tool payloads |
| 9 | **Eval & Deployment** | LLM-as-a-judge (10 traces) + FastAPI webhook + Docker |

## 🏗️ Architecture

```
User Message
    │
    ▼
┌──────────┐     ┌────────────────┐
│ Reasoning│────▶│ Route Decision │
│   Node   │     └──────┬─────────┘
└──────────┘            │
       ▲         ┌──────┼──────────┐
       │         ▼      ▼          ▼
       │      [tools] [hitl]     [end]
       │         │      │
       │    Pre-Hook  Interrupt
       │         │    (approve?)
       │    Execute     │
       │         │      ▼
       │    Post-Hook  Tools
       │         │      │
       │    Compact?────┘
       │         │
       └─────────┘
```

## 🚀 Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure API keys
```bash
cp .env.example .env
# Edit .env and add your GROQ_API_KEY
```

### 3. Run the interactive agent
```bash
python main.py
```

### 4. Run without MCP (faster startup)
```bash
python main.py --no-mcp
```

## 📡 API Server

```bash
uvicorn app:app --host 0.0.0.0 --port 7860
```

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/webhook` | Send a message to the agent |
| `POST` | `/approve` | Approve/reject a pending HITL action |
| `GET` | `/health` | Health check |

### Example request
```bash
curl -X POST http://localhost:7860/webhook \
  -H "Content-Type: application/json" \
  -d '{"message": "Check server health for prod-1"}'
```

## 📊 Run Evaluation
```bash
python -m eval.judge
```
Grades the agent's Error Recovery across 10 synthetic traces (1-5 scale).

## 🐳 Docker Deployment
```bash
docker build -t devops-agent .
docker run -p 7860:7860 --env-file .env devops-agent
```

### Deploy to Hugging Face Spaces
1. Create a new Space (Docker SDK)
2. Push this repo
3. Set `GROQ_API_KEY` in Space settings → Secrets

## 📁 Project Structure

```
├── agent/
│   ├── state.py          # Task 1 — AgentState TypedDict
│   ├── reasoning.py      # Task 2 — LLM + System Prompt
│   ├── tools.py          # Task 3 — Local tool functions
│   ├── mcp_client.py     # Task 4 — MCP client (tool discovery)
│   ├── hooks.py          # Task 5 — Pre/Post lifecycle hooks
│   ├── hitl.py           # Task 6 — Human-in-the-loop node
│   ├── compaction.py     # Task 7 — Context summarization
│   └── graph.py          # Full LangGraph wiring
├── mcp_server/
│   └── server.py         # Task 4 — MCP server (stdio)
├── telemetry/
│   └── tracing.py        # Task 8 — Langfuse integration
├── eval/
│   └── judge.py          # Task 9a — LLM-as-a-judge
├── app.py                # Task 9b — FastAPI endpoint
├── main.py               # Interactive terminal demo
├── Dockerfile            # Task 9b — Container
├── requirements.txt
└── .env.example
```

## 🔑 Required API Keys

| Service | Free Tier | Get Key |
|---------|-----------|---------|
| Groq | ✅ | [console.groq.com](https://console.groq.com) |
| Langfuse | ✅ | [cloud.langfuse.com](https://cloud.langfuse.com) |

## Tools Available

### Local Tools (Task 3)
- `check_server_health` — CPU, memory, disk metrics
- `search_logs` — Search by keyword + severity filter
- `run_deployment` — Deploy a service version (requires HITL approval)

### MCP Tools (Task 4 — dynamically discovered)
- `create_incident_ticket` — Create tickets with priority
- `get_incident_summary` — Past incident details
- `get_service_status` — Microservice status by environment
