---
title: Onboarding
description: Wire NullRun into an existing agent in fifteen minutes: install, key, decorate, set a budget, ship.
---

# First agent

This is the recommended path from "I have an LLM app" to "NullRun is
gating my spend and tools". Each step links out to deeper docs only
when you need them.

## 1. Sign up and create an API key

1. Go to [nullrun.io](https://nullrun.io) and sign in.
2. In the sidebar, under **Access**, open **API keys**, then click
   **New API key** in the top right.
3. Pick a name (e.g. `"my-first-agent"`) and the workflow you want the
   key bound to. Each key is **workflow-scoped** — it represents one
   agent run, not one workspace.
4. Copy the key (`nr_live_…`) shown once and store it somewhere safe
   (env var, secret manager). You'll need it in step 3.

<figure class="nr-shot">
  <img class="nr-shot__light" src="../../assets/images/screenshots/api-key-new-light.png"
       alt="NullRun New API key dialog, with the workflow dropdown and key name field.">
  <img class="nr-shot__dark" src="../../assets/images/screenshots/api-key-new-dark.png"
       alt="NullRun New API key dialog, with the workflow dropdown and key name field.">
  <figcaption class="nr-shot__caption">API keys · New key</figcaption>
</figure>

## 2. Install the SDK

```bash title="shell"
pip install nullrun
```

The plain `nullrun` package covers the full HTTP-level instrumentation
(httpx hook for OpenAI, Azure, Anthropic, Mistral, Gemini, Cohere,
Bedrock) and the auto-patch path for LangGraph, LangChain, OpenAI
Agents, LlamaIndex, CrewAI, and AutoGen. **No vendor extra is required**
— the SDK uses URL-keyed extractors, not vendor-package imports, for
all of the LLM providers above. See [Install](install.md#optional-extras)
for the full list of extras and when you would still need one.

## 3. Wire NullRun into your code

Pick the pattern that matches what you have today:

### A. You already call `client.chat.completions.create(...)`

```python title="my_agent.py"
from openai import OpenAI
from nullrun import protect

client = OpenAI()

# @protect gates every call through NullRun before it runs.
# The runtime is created lazily on the first protected execution
# from NULLRUN_API_KEY, the HTTP instrumentation is installed,
# and tracking starts.
@protect
def answer(prompt: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content


# `init()` auto-registers `shutdown()` via `atexit`, so a clean WS
# close happens on process exit without any explicit call. For a
# CLI script that wants fail-fast on missing config, call
# `nullrun.init(fail_on_exit=True)` instead.
if __name__ == "__main__":
    with nullrun.guard():
        print(answer("What does NullRun do?"))
        # guard() prints the structured 4-line developer report
        # on any NullRunError, then sys.exit(1).
```

Every call inside `answer()` is cost-attributed. `@protect` is the
**gate** (budget pre-flight + kill check + sensitive-tool decision),
not the tracking mechanism — tracking is handled automatically by
auto-instrumentation.

### B. You use a framework (LangGraph / CrewAI / OpenAI Agents / AutoGen / LlamaIndex)

Auto-instrumentation does the same thing — see
[Use with LangGraph](../how-to/langgraph.md) or any of the other
[framework how-tos](../how-to/llm-frameworks.md).
The framework hook subscribes itself on the first `@protect` call.

## 4. Set a budget

In the dashboard, open the workflow your key is bound to and set a
`budget_cents`. A reasonable starter budget:

| Use case | Suggestion |
|---|---|
| Personal / dev experiment | `500` ($5) per period |
| Single-tenant internal tool | `2000` ($20) per period |
| Customer-facing AI feature | `10000` ($100) per period with alerts |

Periods are either calendar-month UTC (Lite) or your billing cycle
(paid plans via Polar). See [Budgets → Period rollover](../concepts/budgets.md)
for the detail.

## 5. Run and observe

```bash title="shell"
python my_agent.py
```

Then open the dashboard → **Workflows** → your workflow → **Executions**.
You'll see every `/gate` call (one per `@protect`-wrapped invocation),
the policy verdict (`allow` / `block` / `rate_limit`), and the cost.

For real-time spend, hit
[`GET /api/v1/orgs/{org_id}/status`](../reference/http-api.md#common-request-patterns)
— it returns `current_spend_cents`, `budget_cents`, `time_to_exhaustion`,
and your plan caps in a single call (see the **Single-call status**
example under "Common request patterns").

## 6. Tighten or loosen

Common next steps, in rough order of how often they're needed:

1. **Block a tool** the agent shouldn't touch — see
   [Tool policies](../concepts/tool-policies.md) and the
   recommended ToolBlock starter list in the
   [Tool catalog](../reference/llm-tool-catalog.md#recommended-toolblock-starter-list).
2. **Allow over-budget for long agents** — see
   [Chain context → soft mode](../concepts/workflow.md#chain-context).
3. **Forward every error to Sentry** — see
   [Error handling → on_error hook](../concepts/error-handling.md).
4. **Pre-flight keys before risky calls** — see
   [Human approval](../concepts/human-approval.md).

## What this walk-through didn't cover

- **Multi-process / multi-key** patterns — see
  [Run multiple agents](../how-to/multi-agent.md).
- **Streaming responses** — see
  [Stream with chain heartbeat](../how-to/streaming.md).

## Where to read next

- [Concepts → Circuit breaker](../concepts/circuit-breaker.md) —
  the mental model behind `@protect`.
- [Concepts → Error handling](../concepts/error-handling.md) — the
  three-layer error model and the structured four-line developer report.
- [Concepts → Workflow context](../concepts/workflow.md) — what the
  `with nullrun.workflow(...)` block does.
