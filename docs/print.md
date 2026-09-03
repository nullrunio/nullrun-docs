---
title: NullRun — printable documentation
description: The complete NullRun documentation in a single page, formatted for printing or saving as PDF.
---

# NullRun documentation

> **To print this page:** press **Ctrl + P** (Windows / Linux) or **⌘ + P** (macOS), or use the button below.
>
> <button class="nr-print-btn" type="button" onclick="window.print()" aria-label="Print this page">🖨 Print this page</button>
>
> **To save as PDF:** in the print dialog, choose *Save as PDF* (Chrome / Edge) or *Save as PostScript* → *PDF* (Safari) as the destination.

This single-page edition contains the full NullRun documentation flattened for printing. Use it as an offline reference — the source-of-truth remains [docs.nullrun.io](https://docs.nullrun.io).

---

## Table of contents

1. [Getting started](#1-getting-started)
   - 1.1 [First agent in 15 minutes](#11-first-agent-in-15-minutes)
   - 1.2 [Installation](#12-installation)
   - 1.3 [Quickstart](#13-quickstart)
   - 1.4 [Configuration](#14-configuration)
2. [Concepts](#2-concepts)
   - 2.1 [Circuit breaker](#21-circuit-breaker)
   - 2.2 [API keys](#22-api-keys)
   - 2.3 [Budgets](#23-budgets)
   - 2.4 [Sensitive tools](#24-sensitive-tools)
   - 2.5 [Error handling](#25-error-handling)
   - 2.6 [Tool policies](#26-tool-policies)
3. [How-to](#3-how-to)
   - 3.1 [Use with FastAPI](#31-use-with-fastapi)
   - 3.2 [Set a hard cost cap](#32-set-a-hard-cost-cap)
   - 3.3 [Stream responses](#33-stream-responses)
   - 3.4 [CI / CD integration](#34-ci-cd-integration)
4. [Reference](#4-reference)
   - 4.1 [Error codes](#41-error-codes)
   - 4.2 [HTTP API](#42-http-api)
   - 4.3 [SDK API](#43-sdk-api)
5. [Compliance](#5-compliance)
   - 5.1 [Compliance overview](#51-compliance-overview)
   - 5.2 [Geographic restrictions](#52-geographic-restrictions)
   - 5.3 [Sanctions screening](#53-sanctions-screening)
6. [Troubleshooting](#6-troubleshooting)

---

# 1. Getting started

## 1.1 First agent in 15 minutes

This is the fastest path from zero to a working, gated agent.

### Step 1 — Install the SDK

```bash
pip install nullrun
```

The SDK requires Python 3.11 or newer.

### Step 2 — Get an API key

Sign in at [nullrun.io](https://nullrun.io), open **API keys**, and create a key. Each key is minted with a public identifier (`nr_live_...`) plus a server-side HMAC secret.

### Step 3 — Wrap your first tool

```python title="app.py"
from openai import OpenAI
from nullrun import init_or_die, guarded, protect, workflow, shutdown

init_or_die(api_key="nr_live_...")        # exits cleanly if api_key missing
client = OpenAI()

with workflow("my-first-agent"):       # scopes the gate to a workflow
    @guarded                           # catches NullRunError, prints
    @protect                           # the catalog user-message,
    def answer(prompt: str) -> str:    # sys.exit(1) — zero boilerplate
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content

if __name__ == "__main__":
    try:
        print(answer("What does NullRun do?"))
    finally:
        shutdown()
```

> The `with workflow("..."):` block binds every `@protect` call inside to a named workflow — required, otherwise the SDK falls back to an ad-hoc `workflow_id` with no budget policy attached. For production, the workflow name should match the dashboard workflow your API key is bound to.

### What gets tracked

- LLM tokens in and out
- Cost in cents (per-call and aggregate)
- Latency
- Tool calls (when using a framework integration)

### Next steps

- Wire NullRun into your existing framework: see [How-to](#3-how-to).
- Set a budget cap: see [Set a hard cost cap](#32-set-a-hard-cost-cap).
- Block a dangerous tool: see [Sensitive tools](#24-sensitive-tools).

## 1.2 Installation

### Python SDK

```bash
pip install nullrun
```

Verify:

```bash
python -c "from nullrun import protect; print('ok')"
```

> **No local mode.** If `init()` is called without an API key, the SDK raises `NullRunAuthenticationError` at first use. There is no offline / local-only fallback.

### API key

Each key is minted with a public identifier (`nr_live_...`) plus a server-side HMAC secret. The SDK transparently obtains the HMAC secret via:

```http
POST /api/v1/auth/verify
```

on first use, so you only need to pass the API key:

```python
import nullrun
nullrun.init(api_key="nr_live_...")
```

The public `init()` surface takes `api_key` (and optionally `api_url`, `debug`). The HMAC secret is **not** a constructor argument — it is read from `NULLRUN_SECRET_KEY` or returned by `/api/v1/auth/verify`.

### Auto-instrumentation

`nullrun.init()` patches the underlying HTTP transport (`httpx`) and the agent framework modules it can detect in `sys.modules`:

| Detected | Coverage |
| --- | --- |
| `openai` ≥ 1.0 | HTTP transport hook |
| `openai-agents` | Agent framework hook |
| `anthropic` | HTTP transport hook |
| `langgraph` | Graph runtime hook (`invoke` / `stream` / `ainvoke` / `astream`) |
| `langchain` | Callback manager hook |
| `llama-index` | LlamaIndex tool/agent hook |
| `crewai` | CrewAI EventBus bridge (1.15+) |

## 1.3 Quickstart

Wrap any function with **`@nullrun.protect`** to track its cost, tools, and behaviour, and let NullRun halt it when it goes off the rails.

```python title="app.py"
from openai import OpenAI
from nullrun import init_or_die, guarded, protect, workflow, shutdown

init_or_die(api_key="nr_live_...")
client = OpenAI()

with workflow("my-first-agent"):
    @guarded
    @protect
    def answer(prompt: str) -> str:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content
```

Every call inside `answer()` is cost-attributed and governed by your workspace policy. On any policy outcome (budget cap, tool block, rate limit, transport outage), `@guarded` prints the catalog wording on stderr and exits `1`.

### What gets tracked

- LLM tokens in and out
- Cost in cents (per-call and aggregate)
- Latency
- Tool calls (when using a framework integration)

## 1.4 Configuration

The SDK accepts configuration through a combination of constructor arguments and environment variables. Environment variables always win.

### Environment variables

| Variable | Purpose | Default |
| --- | --- | --- |
| `NULLRUN_API_KEY` | API key (`nr_live_...`) | *none — required* |
| `NULLRUN_SECRET_KEY` | HMAC secret (returned by `/api/v1/auth/verify`) | *fetched automatically* |
| `NULLRUN_API_URL` | Gateway base URL | `https://api.nullrun.io` |
| `NULLRUN_DEBUG` | Verbose logging | `0` (off) |
| `NULLRUN_LOG_LEVEL` | Log level (`debug` / `info` / `warn` / `error`) | `info` |

### Programmatic configuration

```python
import nullrun
nullrun.init(
    api_key="nr_live_...",
    api_url="https://api.nullrun.io",  # override for staging
    debug=False,
)
```

---

# 2. Concepts

## 2.1 Circuit breaker

The circuit breaker stops your agent when something goes wrong. When the agent is hitting the budget cap, calling a tool your policies forbid, or being asked by an operator to stop — the gate returns `block` and the SDK raises an exception, even if the agent's code doesn't know to stop.

The underlying mechanism is a single `/api/v1/gate` evaluation per `@protect`-wrapped call that returns `allow` / `block` / `require_approval`.

In the dashboard, a tripped breaker shows up as the workflow's status flipping from **Active** to **Killed** or as a flood of **block** decisions in the **Audit log**.

### When does it trip?

The gate reacts to three categories of situation. Each is a separate decision path inside `/gate`, but to you it all looks the same: the next call rejects.

| Situation | What you see | Where in the dashboard |
|---|---|---|
| **Budget exceeded** (Hard mode) | Every call returns `block`; SDK raises `NullRunBudgetError` with `error_code = "NR-B004"` | Audit log, then the spend bar hits 100% |
| **Tool blocked** by policy | `block`; SDK raises `NullRunToolBlockedError` with `error_code = "NR-T001"` | Audit log |
| **Operator kill** | `WorkflowKilledInterrupt` raised mid-call | Workflow status flips to **Killed** |

### What the agent sees

When the breaker trips, the SDK raises an exception. The exact exception depends on what tripped it:

| Trip cause | Exception | `BaseException`? |
|---|---|---|
| Budget exceeded | `NullRunBudgetError` (`error_code = "NR-B004"`) | No |
| Tool blocked | `NullRunBlockedException` (`error_code = "NR-T001"`) | No |
| Operator kill | `WorkflowKilledInterrupt` | **Yes** |

The kill signal is a `BaseException`, not an `Exception`, so it propagates through `try/except Exception:` blocks.

### When the breaker recovers

After the gateway comes back, the gate transitions automatically to normal mode. No operator action needed — the next `/gate` call succeeds if the policy allows it.

If the gate is blocking too often (every call rejects), look at:

1. The **Audit log** for the workflow. The reason column tells you why each call was blocked.
2. The workflow's **Overview** tab — the spend vs. cap bar shows whether you're consistently hitting the budget. Raise the cap or switch to a cheaper model if so.
3. **Effective policy** (on the **Policies** tab). A policy you added recently may be too strict — try narrowing patterns or scoping to one workflow before rolling out org-wide.

## 2.2 API keys

API keys identify who is making a request. They are the only credential your code needs to talk to the gateway — the HMAC secret is fetched automatically.

### Key anatomy

Every key has three parts:

- **Public ID** — `nr_live_abc123...` — shown in the dashboard, safe to log
- **HMAC secret** — returned by `/api/v1/auth/verify` once at first use, stored locally
- **Bound workflows** — the dashboard workflows this key is allowed to act on (set in the **API keys** page)

### Creating a key

In the dashboard: **Settings → API keys → New key**.

You can optionally bind a key to one or more workflows. An unbound key has access to all workflows in the org. Bound keys are restricted to the listed workflows — a request with a `workflow_id` not on the list returns `403 forbidden`.

### Rotation

Keys can be rotated at any time from the **API keys** page. Rotation does not break in-flight requests (the old secret is honored for a 5-minute grace period), but the new secret is required for all subsequent `/auth/verify` calls.

### Revocation

Revoking a key is immediate and irreversible. Any in-flight SDK call will fail on the next `/gate` request.

## 2.3 Budgets

A **budget** is the most important number on the dashboard. It's the maximum amount of money a workflow is allowed to spend in a billing period. Set it too low and your agent stops working. Set it too high and a runaway agent burns through real money before you notice.

### Where you see it

On the **Workflows** detail page, the budget appears as a progress bar near the top:

```
Spend this period         $47.30 of $50.00  (95%)
████████████████████████░░
Time to exhaustion         ~16 hours at current rate
```

Three numbers:

- **Spend this period** — total cents spent since the last period rollover. Resets automatically.
- **Budget** — the cap. Set this in workflow settings.
- **Time to exhaustion** — at the current rate of spend, when the budget will run out.

### What the budget covers

The budget covers **spend**, not calls. Calls are rate-limited separately.

"Spend" is calculated from token counts reported by your LLM provider:

- **Input tokens** × input rate
- **Output tokens** × output rate
- **Cache read** / **cache write** tokens (if your provider exposes them) at their respective rates
- **Reasoning tokens** for o1/o3-style models at the reasoning rate

The total spend is the sum across all `@protect` calls inside the workflow, across the current period.

### Periods

A "period" is the window after which the spend counter resets. NullRun has two period sources:

| Plan | Period source | When it resets |
|---|---|---|
| **Lite** (free) | Calendar month UTC | 1st of each month at 00:00 UTC |
| **Paid** (Starter / Growth / Scale) | Your billing cycle (Polar subscription) | Set when you subscribed; on renewal |

### Hard vs soft mode

**Hard mode (default):** the gate returns `block` the moment the projected cost of the next call exceeds the remaining budget. The agent stops cleanly at the boundary. No partial charge.

**Soft mode:** lets the agent run past its budget when an active chain is present, up to the configured overdraft cap (`max_overdraft_cents` or `max_overdraft_percent`, whichever is lower). The chain returns to standard Hard mode once the cap is exhausted.

## 2.4 Sensitive tools

NullRun lets you declare certain tools as **sensitive** — actions whose blast radius is large enough that a human should look at them before they execute.

A sensitive tool never runs without a human approval. The agent calls the tool, the gate returns `require_approval`, and the SDK raises an exception. The actual tool call only runs once an operator approves it in the dashboard or via Slack.

### Declaring a tool as sensitive

In the **Policies** tab, add a `SensitiveTool` rule. The match expression supports:

| Match type | Syntax | Example |
|---|---|---|
| Exact name | `"name"` | `"send_email"` |
| Glob | `"name:*"` | `"shell:*"` |
| All tools of a server | `"mcp_server:github/*"` | `"mcp_server:github/*"` |

### Approving a pending call

Two surfaces:

- **Dashboard:** the workflow's **Approvals** tab lists every pending call. Click **Approve** or **Reject**.
- **Slack:** if Slack is connected, every pending approval posts a message with **Approve** / **Reject** buttons.

### Audit

Every approval — granted or denied — writes an `audit_events` row with the tool name, the prompt that triggered it, the policy version, and the operator's identity. The audit log is append-only and never editable.

## 2.5 Error handling

The SDK surfaces errors in three layers. You can pick any layer depending on how much control you want over the user-facing message.

### Layer 1 — Structured exceptions

Every public SDK exception inherits from `NullRunError` and carries four structured fields: `error_code` (machine-readable, e.g. `"NR-B004"`), `user_action` (imperative hint), `retryable` (bool), `docs_url`.

```python
from nullrun import NullRunBudgetError
from nullrun.exceptions import NullRunBlockedException

try:
    answer("...")
except NullRunBudgetError as e:
    print(f"Out of budget ({e.error_code}). Action: {e.user_action}")
except NullRunBlockedException as e:
    print(f"Tool blocked: {e.reason}")
```

### Layer 2 — `on_error` hook

Pass a callable to `init()` to centralize error handling:

```python
def my_error_handler(exc: NullRunError) -> None:
    log.error("nullrun: %s (%s)", exc, exc.error_code)
    notify_oncall(exc)

nullrun.init(api_key="nr_live_...", on_error=my_error_handler)
```

The hook fires for every SDK-raised exception before it bubbles up.

### Layer 3 — `@guarded` + `format_user_message`

The zero-boilerplate path. `@guarded` catches every SDK exception, formats a user-friendly message with `format_user_message`, prints it to stderr, and exits `1`.

```python
@guarded
@protect
def answer(prompt):
    ...
```

For programmatic use, `format_user_message(exc)` returns a single-line string suitable for showing to an end user.

### The three exception markers

| Marker | Catches | When to use |
|---|---|---|
| `NullRunError` | Everything | Catch-all in top-level handlers |
| `NullRunDecision` | Expected policy outcomes (budget, block, pause) | When your code can react meaningfully |
| `NullRunInfrastructureError` | System failures (transport, 5xx, auth, config) | When you want to retry / fail loud |

## 2.6 Tool policies

A **tool policy** is a named, versioned bundle of rules that the gate evaluates on every call. Policies live on the server — the SDK never sees them.

### Rule types

| Rule | Purpose | Example |
|---|---|---|
| `ToolBlock` | Block specific tool names or globs | `["shell:*", "fs:rm*"]` |
| `SensitiveTool` | Require approval for specific tools | `["send_email", "github:create_pr"]` |
| `BudgetLimit` | Per-workflow spend cap | `max_budget_cents: 5000` |
| `RateLimit` | Per-minute call cap | `calls_per_minute: 60` |

### Policy version

Every time you change a rule, the policy version bumps. The audit log records which version was active when each call was made. You can roll back to any previous version from the **Policies** tab.

### Effective policy

The gate evaluates the **effective** policy — the union of:

1. The workflow's explicit policy
2. The org's default policy
3. Any seat-scoped overrides

The **Effective policy** tab on a workflow shows the resolved set so you can see exactly what's being enforced.

---

# 3. How-to

## 3.1 Use with FastAPI

The recommended pattern for a long-running FastAPI service:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from nullrun import init, shutdown, protect, workflow

@asynccontextmanager
async def lifespan(app: FastAPI):
    init(api_key="nr_live_...")
    yield
    shutdown()

app = FastAPI(lifespan=lifespan)

@app.post("/ask")
async def ask(prompt: str):
    with workflow("ask-api"):
        @protect
        async def call_openai(p: str) -> str:
            ...
        return await call_openai(prompt)
```

The `lifespan` block ensures `init()` runs once at startup and `shutdown()` flushes pending telemetry at shutdown. The `workflow("ask-api")` context scopes all calls inside the request handler to the `ask-api` workflow in the dashboard.

## 3.2 Set a hard cost cap

The fastest path: open the workflow in the dashboard, click **Settings → Budget**, set `max_budget_cents` to your cap. Default is `0` (unlimited at the workflow level — the org plan cap still applies).

For a code-first workflow, add a `BudgetLimit` rule to your policy:

```json
{
  "type": "BudgetLimit",
  "max_budget_cents": 5000,
  "enforcement": "hard"
}
```

Upload via the dashboard or via `POST /api/v1/workflows/{id}/policy`.

Once the cap is hit, every subsequent `@protect` call raises `NullRunBudgetError` (NR-B004) until the period rolls over.

## 3.3 Stream responses

The SDK supports streamed LLM responses through the same gate. Wrap the streaming call with `@protect` like any other — the gate reserves the projected cost up front and reconciles to actual on stream completion.

```python
@protect
def stream_answer(prompt: str):
    stream = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        stream=True,
    )
    for chunk in stream:
        yield chunk.choices[0].delta.content or ""
```

The gate returns `block` before the stream opens if the budget is exhausted. The actual cost (after the stream completes) is reconciled against the reservation; if the actual is lower than reserved, the difference rolls back into the budget.

## 3.4 CI / CD integration

Add NullRun to your CI to catch regressions in agent cost, tool calls, and approval behaviour before they reach production.

### Pattern 1 — Gate a smoke test

```yaml
- name: Agent smoke test (gated)
  run: |
    export NULLRUN_API_KEY=${{ secrets.NULLRUN_API_KEY_CI }}
    pytest tests/test_agent_smoke.py --nullrun-workflow=ci-smoke
```

The `--nullrun-workflow=ci-smoke` flag binds every test call to a dedicated workflow. The CI workflow has its own budget cap and audit log; a runaway test never touches your production budget.

### Pattern 2 — Fail on budget regression

```yaml
- name: Agent cost regression check
  run: |
    python scripts/agent_cost_check.py --max-cost-cents=200
```

The script wraps a known prompt set in `@protect`, runs them, and exits non-zero if the total exceeds `--max-cost-cents`. Use it to block PRs that significantly shift the cost profile.

---

# 4. Reference

## 4.1 Error codes

The canonical `ApiErrorCode` enum is the source of truth for every non-2xx response the gateway returns.

There are **two parallel taxonomies**:

- **Gateway error slugs** — short SCREAMING_SNAKE_CASE strings in the `error` field of every non-2xx response.
- **NR-* codes** — the SDK's user-facing `error_code` field on every exception.

### Gateway error codes (`error` field)

| `error` slug | HTTP | When | SDK exception |
| --- | --- | --- | --- |
| `bad_request` | 400 | Generic 400 — invalid input that isn't a validation failure | `NullRunConfigError` |
| `unauthorized` | 401 | Missing or invalid `X-API-Key` / expired session / HMAC mismatch | `NullRunAuthenticationError` |
| `forbidden` | 403 | Authenticated but not allowed (incl. CSRF mismatch) | `NullRunAuthenticationError` |
| `not_found` | 404 | Resource doesn't exist or isn't visible | (caller handles) |
| `conflict` | 409 | Idempotency conflict, duplicate, "already a member" | `NullRunError` |
| `validation_error` | 422 | Request body / params failed schema validation | `NullRunConfigError` |
| `plan_limit_exceeded` | 422 | Plan cap hit. Body `details.resource` carries dimension. | `NullRunBlockedException` |
| `rate_limit_exceeded` | 429 | Per-minute / per-day rate cap. Body carries `retry_after`. | `RateLimitError` |
| `internal_error` | 500 | Server-side bug | `NullRunBackendError` (retryable) |
| `not_implemented` | 501 | Feature not yet implemented | `NullRunError` |
| (also `internal_error`) | 503 | Transient downstream failure on an enforcement path | `NullRunBackendError` (retryable) |

### NR-* error code catalog

| Code | Class | When |
| --- | --- | --- |
| `NR-B001` | Budget | Budget reservation failed |
| `NR-B002` | Budget | Soft-mode overdraft exhausted |
| `NR-B003` | Budget | Plan cap exceeded |
| `NR-B004` | Budget | Budget exceeded (hard mode) |
| `NR-T001` | Tool block | Tool in block list |
| `NR-T002` | Tool block | Sensitive tool — awaiting approval |
| `NR-T003` | Tool block | Tool not in catalog |
| `NR-R001` | Rate limit | Per-minute rate cap exceeded |
| `NR-R002` | Rate limit | Per-day rate cap exceeded |
| `NR-A001` | Auth | Missing API key |
| `NR-A002` | Auth | HMAC signature mismatch |
| `NR-A003` | Auth | Key revoked |
| `NR-N001` | Network | Gateway unreachable |
| `NR-N002` | Network | Request timeout |
| `NR-K001` | Kill | Workflow killed by operator |
| `NR-K002` | Kill | Workflow paused by operator |

### SDK exception hierarchy

```
NullRunError                          (Exception)
├── NullRunDecision                   (marker — expected policy outcomes)
│   ├── NullRunBlockedException       (policy / budget / loop / sensitive block)
│   │   ├── NullRunBudgetError        (budget exhausted — NR-B004)
│   │   └── NullRunToolBlockedError   (tool in block list — NR-T001)
│   └── WorkflowPausedException       (paused via control plane)
└── NullRunInfrastructureError        (marker — system failures)
    ├── NullRunConfigError            (misconfiguration, e.g. missing api_key)
    ├── NullRunAuthenticationError   (401 / 403)
    │   └── NullRunAuthError          (401 specifically)
    └── NullRunTransportError         (transport failures)
        ├── NullRunBackendError       (5xx — retryable)
        └── RateLimitError            (429 — carries .retry_after, .upgrade_url)

BaseException
└── WorkflowKilledException           (parent)
    └── WorkflowKilledInterrupt       (kill via control plane — BaseException)
```

## 4.2 HTTP API

The gateway exposes a small REST surface. Every request requires:

- `Authorization: Bearer nr_live_...` (machine)
- `X-NULLRUN-PROTOCOL: 3` (mandatory version header)

### `POST /api/v1/gate`

The hot path. Called by the SDK on every `@protect`-wrapped call.

**Request:**

```json
{
  "workflow_id": "my-first-agent",
  "tool_name": "openai.chat",
  "tool_args": {"model": "gpt-4o-mini", "messages": [...]},
  "projected_cost_cents": 2
}
```

**Response:**

```json
{
  "decision": "allow",
  "execution_id": "0192f7b3-7c5d-7e8a-b1f4-...",
  "remaining_budget_cents": 4760
}
```

Possible `decision` values: `allow`, `block`, `require_approval`.

### `POST /api/v1/executions/{id}/track`

Called by the SDK after the tool returns, to reconcile the actual cost.

**Request:**

```json
{
  "actual_cost_cents": 1,
  "tokens_in": 142,
  "tokens_out": 89,
  "status": "ok"
}
```

**Response:** `204 No Content`.

### `POST /api/v1/auth/verify`

One-shot key bootstrap. Returns the HMAC secret bound to the supplied API key.

### `POST /api/v1/workflows/{id}/kill`

Operator-only. Immediately trips the breaker on the named workflow. Subsequent `/gate` calls return `block` with `error_code = "NR-K001"`.

### `POST /api/v1/workflows/{id}/resume`

Operator-only. Clears the kill flag. Subsequent `/gate` calls resume normally.

## 4.3 SDK API

The Python SDK exposes the following public surface:

### Module-level

| Name | Purpose |
| --- | --- |
| `init(api_key, api_url=None, debug=False, on_error=None)` | Bootstrap the SDK. Idempotent. |
| `init_or_die(api_key, ...)` | Same as `init()`, but `sys.exit(1)` if the key is missing or invalid. |
| `shutdown()` | Flush pending telemetry, close HTTP pool. Idempotent. |
| `workflow(name)` | Context manager. Binds every `@protect` call inside to `name`. |
| `protect(fn=None, *, tool_name=None)` | Decorator. Wraps `fn` so every call passes through `/gate`. |
| `guarded(fn=None)` | Decorator. Catches `NullRunError`, prints user message, `sys.exit(1)`. |

### Exceptions

All exceptions live in `nullrun.exceptions` (re-exported from `nullrun`):

```python
from nullrun import (
    NullRunError,
    NullRunDecision,
    NullRunBlockedException,
    NullRunBudgetError,
    NullRunToolBlockedError,
    NullRunInfrastructureError,
    NullRunConfigError,
    NullRunAuthenticationError,
    NullRunAuthError,
    NullRunTransportError,
    NullRunBackendError,
    RateLimitError,
    WorkflowKilledException,
    WorkflowKilledInterrupt,
)
```

### Helper functions

| Name | Purpose |
| --- | --- |
| `format_user_message(exc)` | Single-line, end-user-safe message for any `NullRunError` |
| `get_workflow_status(name)` | Returns the current status of the named workflow (cached) |
| `get_effective_policy(name)` | Returns the resolved policy currently enforced on `name` |

---

# 5. Compliance

## 5.1 Compliance overview

NullRun ships with two built-in compliance gates:

1. **Geographic restrictions** — block traffic from countries on your blocklist (or allow only countries on your allowlist).
2. **Sanctions screening** — block traffic from individuals or entities on OFAC, EU, UK, and UN sanctions lists.

Both gates are **off by default**. Enable them in **Settings → Compliance**.

When a request is blocked by a compliance gate, the SDK raises `NullRunBlockedException` with `error_code = "NR-C001"` (geo) or `NR-C002"` (sanctions). The decision is recorded in the audit log with the gate that fired.

## 5.2 Geographic restrictions

Block (or allow) requests based on the geolocation of the request origin. The location is derived from the source IP at the gateway edge.

### Blocklist mode

Drop a list of ISO 3166-1 alpha-2 country codes into the blocklist. Requests from those countries return `block` with `error_code = "NR-C001"`.

### Allowlist mode

Drop a list of ISO 3166-1 alpha-2 country codes into the allowlist. **All other countries are blocked.** Use allowlist mode when your product is only available in a defined jurisdiction.

### Audit

Every block records the country code and the gate mode (blocklist / allowlist) in `audit_events`.

## 5.3 Sanctions screening

Sanctions screening matches the request origin against the consolidated OFAC / EU / UK / UN sanctions lists. The list is refreshed every 24 hours from the official sources.

### Match modes

- **Block on match:** the request is rejected. Default.
- **Require approval on match:** the request is paused until an operator approves.
- **Log only:** the request proceeds; the match is recorded in the audit log.

### False positives

If you believe a match is incorrect, file a dispute from the **Audit log → row → Dispute**. The dispute is reviewed by the NullRun compliance team within one business day.

---

# 6. Troubleshooting

### "My agent suddenly stopped responding"

Open the workflow in the dashboard. Check the status:

| Status | What happened |
|---|---|
| **Active** | The agent is fine — check the application logs for the actual error |
| **Paused** | You paused it (or an operator did). Click **Resume** to restart. |
| **Killed** | You killed it (or an operator did). Create a new workflow or re-activate. |

If the status is **Active** but every call rejects, open the **Audit log** and check the `reason` column.

### `NullRunAuthenticationError` on the first call

The SDK couldn't reach `/api/v1/auth/verify`. Check:

1. `NULLRUN_API_KEY` is set and starts with `nr_live_`.
2. The dashboard workflow exists and your API key is bound to it.
3. Your environment can reach `https://api.nullrun.io` (firewall / proxy).

### `NullRunBudgetError` on every call

The workflow has hit its budget cap. Two options:

- Wait for the period to roll over.
- Raise the cap in **Settings → Budget**.

### `RateLimitError` with `retry_after` set

You're calling too fast. The SDK surfaces `.retry_after` (seconds) on the exception. The default handler `@guarded` honours it.

### Gateway timeout (`NullRunTransportError`)

The gateway took too long to respond. The SDK retries with exponential backoff up to 3 times. After that, the exception bubbles.

If you see this repeatedly:

1. Check [status.nullrun.io](https://status.nullrun.io) for incidents.
2. Verify your network egress to `api.nullrun.io`.
3. If your call projects a high cost (>1000 tokens), consider splitting it.

### "My sensitive-tool approval never arrives"

Check the **Approvals** tab. If the row is missing:

- The call never reached the gate (check application logs for the `protect` invocation).
- The `tool_name` doesn't match the policy pattern — check **Effective policy**.

If the row is present but no operator acts on it:

- Confirm Slack is connected (the Slack channel is the default escalation path).
- Check the operator's notification settings in **Settings → Notifications**.

### Workflow paused unexpectedly

Two causes:

1. An operator clicked **Pause** in the dashboard or via Slack.
2. The workflow exceeded its `max_pause_minutes` (set in **Settings → Workflow**).

Click **Resume** in the **Control** panel to restart.

---

*End of printable documentation.*

*This document was generated from [docs.nullrun.io](https://docs.nullrun.io). For the latest version, always refer to the live site.*
