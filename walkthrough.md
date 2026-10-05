# 🏃‍♂️ Smart DevOps Agent — Quick Walkthrough

This guide provides crisp, step-by-step instructions to run, test, and present the agent for your assessment.

---

## 1. 🔑 Pre-requisites

Before running the agent, you need your API keys.

1. **Create the `.env` file:**
   Copy `.env.example` to `.env`.
2. **Add Groq Key (Required for LLM):**
   Get a free key from [console.groq.com](https://console.groq.com) and set `GROQ_API_KEY`.
3. **Add Langfuse Keys (Required for Task 8 Telemetry):**
   Get free keys from [cloud.langfuse.com](https://cloud.langfuse.com) and set `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY`.

---

## 2. 💻 How to Run

### Option A: Interactive Terminal (Best for Demo)
Runs a command-line chat interface where you can talk to the agent.
```bash
python main.py
```
*(If the MCP server is failing to start, run `python main.py --no-mcp` to run with only local tools).*

### Option B: FastAPI Server (Best for Deployment / Integration)
Runs the agent as a web service.
```bash
uvicorn app:app --host 0.0.0.0 --port 7860
```
- Send a message: `POST http://localhost:7860/webhook` with `{"message": "hi"}`
- Approve a deployment: `POST http://localhost:7860/approve` with `{"thread_id": "...", "decision": "approve"}`

---

## 3. 🧪 How to Demo the 9 Tasks

During your assessment, use these exact prompts in the `main.py` terminal to prove every requirement works:

### Task 1 & 2: State & Reasoning
> **You:** "What can you do?"
*Agent will explain its capabilities using the system prompt.*

### Task 3: Local Tools
> **You:** "Check server health for prod-1"
*Agent calls `check_server_health` tool and returns metrics.*

### Task 4: MCP (Dynamic Tools)
> **You:** "Get the summary for incident INC-001"
*Agent calls the `get_incident_summary` tool which is hosted on the external MCP server.*

### Task 5: Lifecycle Hooks (Guardrails)
> **You:** "Search logs for DROP TABLE users"
*The **Pre-hook** intercepts the dangerous keyword, blocks the tool, and returns a 400 error. The agent self-corrects and apologizes.*

> **You:** "Create a high priority ticket for database outage"
*The ticket is created. Look closely at the response — the **Post-hook** appended an `[AUDIT]` timestamp to the result.*

### Task 6: Human-in-the-Loop (HITL)
> **You:** "Deploy auth-service version 2.1.0"
*The LangGraph execution will PAUSE. The terminal will warn you that a high-stakes action requires approval. Type `approve` to proceed, or `reject` to block it.*

### Task 7: Context Compaction
> **You:** *(Send 10+ short messages to fill up the state)*
*Once the message list exceeds 10 items, the agent will silently trigger the `compact_node`. It summarizes the oldest messages into a single paragraph to save tokens.*

### Task 8: Telemetry
Go to your **Langfuse Dashboard**. You will see a live trace of your entire conversation, including exact token counts, latency graphs, and the raw JSON of the tool calls.

---

## 4. 📈 Task 9a: Running the Evaluation

To prove you built an LLM-as-a-judge system:
```bash
python -m eval.judge
```
This script feeds 10 historical conversation traces (simulating errors, HITL rejections, etc.) to the LLM and asks it to score the agent's "Error Recovery" out of 5. The results are saved to `eval/results.json`.

---

## 5. 🐳 Task 9b: Deployment

To prove production readiness, the project includes a `Dockerfile`.

**Local Docker Test:**
```bash
docker build -t devops-agent .
docker run -p 7860:7860 --env-file .env devops-agent
```

**Deploy to Hugging Face Spaces (Free):**
1. Create a new Space at [huggingface.co/spaces](https://huggingface.co/spaces).
2. Select **Docker** as the space SDK.
3. Upload the project files.
4. Go to Settings -> Variables and Secrets -> Add your `GROQ_API_KEY`.
