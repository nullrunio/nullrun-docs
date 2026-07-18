# First agent in 15 minutes

This is the recommended path from "I have an LLM app" to "NullRun is
gating my spend and tools". Skip the deep dives — link to them when
you actually need them.

## 1. Sign up and create an API key (2 min)

1. Go to [nullrun.io](https://nullrun.io) and sign in.
2. Open **API keys** → **Create key**.
3. Pick a name (e.g. `"my-first-agent"`) and the workflow you want the
   key bound to. Each key is **workflow-scoped** since Phase 139 —
   it represents one agent run, not one workspace.
4. Copy the key (`nr_live_…`) shown once and store it somewhere safe
   (env var, secret manager). You'll need it in step 3.

## 2. Install the SDK (1 min)

```bash title="shell"
pip install "nullrun[openai]"     # raw openai SDK + tracking
pip install "nullrun[langgraph]"  # if you're using LangGraph
pip install "nullrun[agents]"     # if you're using OpenAI Agents SDK
pip install "nullrun[all]"        # every vendor extra — heaviest install
```

See [Install](install.md#optional-extras) for the full list of extras.
For this walk-through `nullrun[openai]` is enough.

## 3. Wire NullRun into your code (5 min)

Pick the pattern that matches what you have today:

### A. You already call `client.chat.completions.create(...)`

```python title="my_agent.py"
import nullrun
from openai import OpenAI
from nullrun import init_or_die, protect, shutdown

# 1. One line — reads NULLRUN_API_KEY from env if not passed.
init_or_die(api_key="nr_live_...")

client = OpenAI()

# 2. @protect gates every call through NullRun before it runs.
@protect
def answer(prompt: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content


# 3. shutdown() flushes pending events and closes the WS cleanly
#    — register via atexit in production scripts.
if __name__ == "__main__":
    try:
        print(answer("What does NullRun do?"))
    finally:
        shutdown()
```

That's the whole integration. Every call inside `answer()` is now
cost-attributed. There is no SDK call you have to remember to make
for tracking — auto-instrumentation picks up the OpenAI HTTP call
automatically. `@protect` is the **gate** (budget pre-flight + kill
check + sensitive-tool decision), not the tracking mechanism.

### B. You use a framework (LangGraph / CrewAI / OpenAI Agents / AutoGen / LlamaIndex)

Auto-instrumentation does the same thing — see
[Use with LangGraph](../how-to/langgraph.md) or any of the other
[framework how-tos](../how-to/auto-instrumented-frameworks.md).
Most of the time the only line you add is the `init()` call.

## 4. Set a budget (1 min)

In the dashboard, open the workflow your key is bound to and set a
`budget_cents`. The default is `0` (every call blocks immediately),
so the agent will fail closed until you set a cap.

A reasonable starter budget:

| Use case | Suggestion |
|---|---|
| Personal / dev experiment | `500` ($5) per period |
| Single-tenant internal tool | `2000` ($20) per period |
| Customer-facing AI feature | `10000` ($100) per period with alerts |

Periods are either calendar-month UTC (Lite) or your billing cycle
(paid plans via Polar). See [Budgets → Period rollover](../concepts/budgets.md)
for the detail.

## 5. Run and observe (2 min)

```bash title="shell"
python my_agent.py
```

Then open the dashboard → **Workflows** → your workflow → **Decisions**.
You'll see every `/gate` call (one per `@protect`-wrapped invocation),
the policy verdict (`allow` / `block` / `rate_limit`), and the cost.

For real-time spend, hit
[`GET /api/v1/orgs/{org_id}/status`](../reference/http-api.md#status)
— it returns `current_spend_cents`, `budget_cents`, `time_to_exhaustion`,
and your plan caps in a single call.

## 6. Tighten or loosen (remaining time)

Common next steps, in rough order of how often they're needed:

1. **Block a tool** the agent shouldn't touch — see
   [Tool policies](../concepts/tool-policies.md) and the
   [recommended `@sensitive` starter list](../reference/llm-tool-catalog.md#recommended-sensitive-starter-list).
2. **Allow over-budget for long agents** — see
   [Chain context → soft mode](../concepts/workflow.md#chain-context-soft-mode-budget-gate).
3. **Forward every error to Sentry** — see
   [Error handling → on_error hook](../concepts/error-handling.md#layer-2-the-on-error-hook-for-observability).
4. **Pre-flight keys before risky calls** — see
   [Human approval](../concepts/human-approval.md).

## What this walk-through didn't cover

- **Multi-process / multi-key** patterns — see
  [Run multiple agents](../how-to/multi-agent.md).
- **Self-hosted gateway** — see your on-prem deployment runbook.
- **Streaming responses** — see
  [Stream with chain heartbeat](../how-to/streaming.md).

## Where to read next

- [Concepts → Circuit breaker](../concepts/circuit-breaker.md) —
  the mental model behind `@protect`.
- [Concepts → Error handling](../concepts/error-handling.md) — the
  three-layer error model.
- [Concepts → Workflow context](../concepts/workflow.md) — what the
  `with nullrun.workflow(...)` block does.
