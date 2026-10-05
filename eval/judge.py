"""
Task 9a: Evaluation — LLM-as-a-Judge

Feeds 10 historical (synthetic) conversation traces to an LLM
and prompts it to grade the agent's "Error Recovery" on a 1-5 scale.

Usage:
    python -m eval.judge
"""

import json
import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage

load_dotenv()

# ── Judge Prompt ─────────────────────────────────────────────────────────────

JUDGE_PROMPT = """\
You are evaluating an AI DevOps agent's **Error Recovery** capability.

Given the conversation trace below, grade the agent on:
1. **Error detection** — Does it notice tool errors or bad parameters?
2. **Self-correction** — Does it retry with fixed parameters after a failure?
3. **Graceful fallback** — Does it give useful info even when tools fail?
4. **Coherence** — Does it stay on track through the error?

Score 1-5:
  1 = Terrible (crashes or nonsense)
  2 = Poor (sees error, doesn't recover)
  3 = Adequate (basic recovery, but clumsy)
  4 = Good (recovers well, retries correctly)
  5 = Excellent (graceful, explains error, provides alternatives)

Return ONLY valid JSON: {{"score": <1-5>, "reasoning": "<your analysis>"}}

Conversation Trace:
{trace}
"""

# ── 10 Synthetic Traces ─────────────────────────────────────────────────────

TRACES = [
    {
        "id": 1,
        "title": "Normal health check — no errors",
        "messages": [
            {"role": "user", "content": "Check health of prod-1"},
            {"role": "assistant", "content": "[tool_call] check_server_health(server_name='prod-1')"},
            {"role": "tool", "content": "Server: prod-1\nStatus: healthy\nCPU: 42%"},
            {"role": "assistant", "content": "prod-1 is healthy — CPU at 42%."},
        ],
    },
    {
        "id": 2,
        "title": "Invalid priority — agent self-corrects",
        "messages": [
            {"role": "user", "content": "Create an urgent ticket for DB outage"},
            {"role": "assistant", "content": "[tool_call] create_incident_ticket(title='DB Outage', description='Database unreachable', priority='urgent')"},
            {"role": "tool", "content": "Error 400: Invalid priority 'urgent'. Must be one of: ['low','medium','high','critical']"},
            {"role": "assistant", "content": "Let me fix the priority. Retrying with 'critical'."},
            {"role": "assistant", "content": "[tool_call] create_incident_ticket(title='DB Outage', description='Database unreachable', priority='critical')"},
            {"role": "tool", "content": '{"ticket_id":"INC-4321","status":"OPEN"}'},
            {"role": "assistant", "content": "Ticket INC-4321 created with critical priority."},
        ],
    },
    {
        "id": 3,
        "title": "SQL injection blocked by pre-hook",
        "messages": [
            {"role": "user", "content": "Search logs for DROP TABLE users"},
            {"role": "assistant", "content": "[tool_call] search_logs(query='DROP TABLE users')"},
            {"role": "tool", "content": "Error 400: Blocked: query contains dangerous keyword 'DROP'. Please rephrase."},
            {"role": "assistant", "content": "That query was blocked for safety. Let me search for 'table deletion' instead."},
            {"role": "assistant", "content": "[tool_call] search_logs(query='table deletion')"},
            {"role": "tool", "content": "[2026-10-05T14:23:01] [ERROR] Connection timeout for query: table deletion"},
            {"role": "assistant", "content": "Found error logs related to table operations."},
        ],
    },
    {
        "id": 4,
        "title": "Deployment rejected by human",
        "messages": [
            {"role": "user", "content": "Deploy auth-service v2.1.0"},
            {"role": "assistant", "content": "This requires human approval. [tool_call] run_deployment(service='auth-service', version='2.1.0')"},
            {"role": "system", "content": "HITL: Human rejected the deployment."},
            {"role": "tool", "content": "Deployment REJECTED by human operator."},
            {"role": "assistant", "content": "The deployment was rejected. I won't proceed unless you explicitly ask again."},
        ],
    },
    {
        "id": 5,
        "title": "Unknown tool called — agent recovers",
        "messages": [
            {"role": "user", "content": "Restart the API server"},
            {"role": "assistant", "content": "[tool_call] restart_server(server='api-server')"},
            {"role": "tool", "content": "Error 404: Unknown tool 'restart_server'"},
            {"role": "assistant", "content": "I don't have a restart tool. Let me check the server health instead and suggest next steps."},
            {"role": "assistant", "content": "[tool_call] check_server_health(server_name='api-server')"},
            {"role": "tool", "content": "Server: api-server\nStatus: warning\nCPU: 88%"},
            {"role": "assistant", "content": "The API server shows high CPU (88%). You may need to restart it manually."},
        ],
    },
    {
        "id": 6,
        "title": "Empty server name — hook catches it",
        "messages": [
            {"role": "user", "content": "Check server health"},
            {"role": "assistant", "content": "[tool_call] check_server_health(server_name='')"},
            {"role": "tool", "content": "Error 400: Server name cannot be empty."},
            {"role": "assistant", "content": "I need a server name. Which server should I check? (e.g. prod-1, staging-2)"},
            {"role": "user", "content": "prod-1"},
            {"role": "assistant", "content": "[tool_call] check_server_health(server_name='prod-1')"},
            {"role": "tool", "content": "Server: prod-1\nStatus: healthy\nCPU: 35%"},
            {"role": "assistant", "content": "prod-1 is healthy with CPU at 35%."},
        ],
    },
    {
        "id": 7,
        "title": "Tool execution exception — 500 error",
        "messages": [
            {"role": "user", "content": "Search logs for 'timeout'"},
            {"role": "assistant", "content": "[tool_call] search_logs(query='timeout', severity='all')"},
            {"role": "tool", "content": "Error 500: Tool execution failed — ConnectionResetError"},
            {"role": "assistant", "content": "The log search service is temporarily unavailable. Let me try again."},
            {"role": "assistant", "content": "[tool_call] search_logs(query='timeout', severity='error')"},
            {"role": "tool", "content": "[2026-10-05T14:23:01] [ERROR] Connection timeout on upstream service"},
            {"role": "assistant", "content": "Found an error log about connection timeouts."},
        ],
    },
    {
        "id": 8,
        "title": "Invalid severity — agent corrects",
        "messages": [
            {"role": "user", "content": "Show me critical logs"},
            {"role": "assistant", "content": "[tool_call] search_logs(query='critical issues', severity='critical')"},
            {"role": "tool", "content": "Error 400: Invalid severity 'critical'. Must be one of: ['info','warning','error','all']"},
            {"role": "assistant", "content": "The severity filter doesn't support 'critical'. Let me use 'error' instead."},
            {"role": "assistant", "content": "[tool_call] search_logs(query='critical issues', severity='error')"},
            {"role": "tool", "content": "[2026-10-05T14:22:55] [ERROR] Database connection pool exhausted"},
            {"role": "assistant", "content": "Found error-level logs about database connection issues."},
        ],
    },
    {
        "id": 9,
        "title": "Multiple tool calls — one fails, one succeeds",
        "messages": [
            {"role": "user", "content": "Check prod-1 health and search for memory errors"},
            {"role": "assistant", "content": "[tool_call] check_server_health(server_name='prod-1')"},
            {"role": "tool", "content": "Server: prod-1\nStatus: warning\nMemory: 89%"},
            {"role": "assistant", "content": "[tool_call] search_logs(query='memory', severity='fatal')"},
            {"role": "tool", "content": "Error 400: Invalid severity 'fatal'. Must be one of: ['info','warning','error','all']"},
            {"role": "assistant", "content": "Health check shows high memory (89%). Log search failed — let me retry with 'error' severity."},
            {"role": "assistant", "content": "[tool_call] search_logs(query='memory', severity='error')"},
            {"role": "tool", "content": "[2026-10-05T14:23:01] [ERROR] Out of memory error in worker process"},
            {"role": "assistant", "content": "prod-1 has 89% memory usage and there are OOM errors in the logs. Consider scaling up."},
        ],
    },
    {
        "id": 10,
        "title": "Deployment approved — full success path",
        "messages": [
            {"role": "user", "content": "Deploy payment-service v3.0.0"},
            {"role": "assistant", "content": "⚠️ This requires human approval. Proceeding with deployment request."},
            {"role": "assistant", "content": "[tool_call] run_deployment(service='payment-service', version='3.0.0')"},
            {"role": "system", "content": "HITL: Human approved the deployment."},
            {"role": "tool", "content": "Deployment Successful!\nService: payment-service\nVersion: 3.0.0\nStatus: RUNNING"},
            {"role": "assistant", "content": "payment-service v3.0.0 deployed successfully and is running with health checks passing."},
        ],
    },
]


# ── Run Evaluation ───────────────────────────────────────────────────────────

def run_evaluation():
    """Grade all 10 traces and print a summary."""
    llm = ChatGroq(
        model="qwen/qwen3.8-27b",
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=0.0,
    )

    results = []
    print("=" * 60)
    print("  📊 LLM-as-a-Judge — Error Recovery Evaluation")
    print("=" * 60)

    for trace in TRACES:
        trace_str = json.dumps(trace["messages"], indent=2)
        prompt = JUDGE_PROMPT.format(trace=trace_str)

        response = llm.invoke([HumanMessage(content=prompt)])

        try:
            # Try to parse the JSON from the response
            text = response.content.strip()
            # Handle markdown code blocks
            if "```" in text:
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()
            evaluation = json.loads(text)
        except (json.JSONDecodeError, IndexError):
            evaluation = {"score": 0, "reasoning": f"Failed to parse: {response.content[:100]}"}

        results.append({
            "trace_id": trace["id"],
            "title": trace["title"],
            "score": evaluation.get("score", 0),
            "reasoning": evaluation.get("reasoning", "N/A"),
        })

        print(f"\n  Trace {trace['id']}: {trace['title']}")
        print(f"  Score: {'⭐' * evaluation.get('score', 0)} ({evaluation.get('score', 0)}/5)")
        print(f"  Reasoning: {evaluation.get('reasoning', 'N/A')[:120]}")

    # ── Summary ──────────────────────────────────────────────────────────
    scores = [r["score"] for r in results if r["score"] > 0]
    avg = sum(scores) / len(scores) if scores else 0

    print("\n" + "=" * 60)
    print(f"  📈 Average Error Recovery Score: {avg:.1f} / 5.0")
    print(f"  📋 Traces Evaluated: {len(results)}")
    print(f"  ✅ Parsed Successfully: {len(scores)}")
    print("=" * 60)

    # Save results to file
    output_path = os.path.join(os.path.dirname(__file__), "results.json")
    with open(output_path, "w") as f:
        json.dump({"average_score": avg, "results": results}, f, indent=2)
    print(f"\n  💾 Results saved to {output_path}")


if __name__ == "__main__":
    run_evaluation()
