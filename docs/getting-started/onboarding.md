---
title: Onboarding
description: Wire NullRun into an existing agent — create a workflow, mint a key, decorate a function, set a budget, and watch the decisions.
maturity: stable
---

# First agent

This is the path from "I have an LLM app" to "NullRun is gating my spend and my tools".

## 1. Create a workspace and a workflow

Sign in at [nullrun.io](https://nullrun.io). The setup wizard walks through five steps: **Workspace**, **Workflow**, **API key**, **Connect**, **Ready**.

1. **Workspace** — name your workspace.
2. **Workflow** — name the workflow your agent runs as. The wizard creates the workflow, a **Budget Limit** policy of `$10` scoped to that workflow, and an API key bound to it.
3. **API key** — the key appears once. Copy it into your shell:

```bash title="shell"
export NULLRUN_API_KEY=nr_live_...
```

The signing secret is never shown again. The SDK fetches it from the gateway on first use.

You can create more keys later under **Access → API keys**. Each key is bound to one workflow.

<figure class="nr-shot">
  <img class="nr-shot__light" src="../../assets/images/screenshots/api-key-new-light.png"
       alt="NullRun New API key dialog, with the workflow dropdown and key name field."
       loading="lazy" decoding="async">
  <img class="nr-shot__dark" src="../../assets/images/screenshots/api-key-new-dark.png"
       alt="NullRun New API key dialog, with the workflow dropdown and key name field."
       loading="lazy" decoding="async">
  <figcaption class="nr-shot__caption">API keys · New key</figcaption>
</figure>

## 2. Install the SDK

```bash title="shell"
pip install nullrun
```

The plain `nullrun` package is enough. It depends on `httpx` and nothing else, and it hooks the providers and frameworks you already use. See [Install → What gets instrumented](install.md#what-gets-instrumented).

## 3. Wire NullRun into your code

### A. You call the provider SDK directly

Decorate the function that calls the provider. The [Quickstart](quickstart.md) has the full example.

`@protect` is the gate: it asks the gateway for a decision, and it stops the call when the answer is no. Cost tracking is separate — the SDK instruments the HTTP client and books the tokens on its own.

`with nullrun.guard():` catches the refusal, prints the message, and exits with code `1`. Use a plain `try` and `except` when your service has to stay up.

`init()` is optional. The first `@protect` call creates the runtime from `NULLRUN_API_KEY`. Call it when you want a missing key to fail at startup. See [Quickstart → Start the runtime yourself](quickstart.md#start-the-runtime-yourself).

### B. You use a framework

Auto-instrumentation covers the same ground. See [Use with LangGraph](../how-to/langgraph.md) and the other [framework how-tos](../how-to/llm-frameworks.md).

## 4. Set the budget

The wizard seeds a Budget Limit policy of `$10` for the new workflow. Open **Governance → Policies** to edit it, or to add another one.

| Use case | Starting cap |
|---|---|
| Personal experiment | `$5.00` (`500` cents) per period |
| Internal tool | `$20.00` (`2000` cents) per period |
| Customer-facing feature | `$100.00` (`10000` cents) per period, with alerts |

A Budget Limit policy has an **Enforcement mode**. `Hard` stops every call once the cap is reached. `Soft` lets calls through inside an overdraft cap.

The period window differs by plan. See [Budgets → Periods](../concepts/budgets.md#periods).

## 5. Run it and watch the decisions

```bash title="shell"
python my_agent.py
```

Then open **Workflows → your workflow → Executions**. Every protected call gets a row. The **Result** column holds the gate verdict, and **Cost** holds what the call cost.

For the raw numbers, `GET /api/v1/orgs/{org_id}/status` returns the spend of the period, the cap, and what is left of it in one call. See [HTTP API → Budget and status](../reference/http-api.md#budget-and-status).

## 6. Tighten or loosen

1. **Block a tool** the agent should not touch — see [Tool policies](../concepts/tool-policies.md) and the starter list in the [Tool catalog](../reference/llm-tool-catalog.md#recommended-toolblock-starter-list).
2. **Ask a human first** on a sensitive action — see [Human approval](../concepts/human-approval.md).
3. **Let a long agent overspend on purpose** — see [Workflows → Chain context](../concepts/workflow.md#chain-context).
4. **Forward every error to your monitoring** — see [Error handling](../concepts/error-handling.md).

## Next

- [5-minute tour → the control center end to end](tour.md)
- [Concepts → Circuit breaker](../concepts/circuit-breaker.md)
- [How-to → Run multiple agents](../how-to/multi-agent.md)
- [How-to → Stream responses](../how-to/streaming.md)
