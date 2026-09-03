---
title: Troubleshooting
description: Common NullRun questions answered: why is my agent blocked, how to debug a gate decision, what to do when a budget doesn't reset.
---

# Troubleshooting

What to expect when NullRun is doing its job — and how to recover
when it isn't.

> **Format:** symptom → diagnosis → fix. If your question isn't here,
> see the [Errors reference](reference/errors.md) or open a ticket
> from the dashboard's **Help → Send feedback** form (include the
> `workflow_id` and the failing row's `decision_id`).

## What can go wrong (and how NullRun reacts)

| Situation | Default behaviour | Exception raised |
| --- | --- | --- |
| Workflow exceeds budget (Hard mode) | Halt at next `/gate` call | `NullRunBudgetError` (`error_code = "NR-B004"`) |
| Soft mode over-budget | Allow bounded overrun if chain active, otherwise block | `NullRunBudgetError` (`error_code = "NR-B004"`) |
| Agent calls a sensitive tool | Block the call before the function body runs (per ToolBlock policy) | `NullRunToolBlockedError` (`error_code = "NR-T001"`) |
| Gateway unreachable, budget gate | **Fail-CLOSED** — 402 | `NullRunBackendError` |
| Gateway unreachable, per-key rate limit | **Fail-OPEN** (secondary signal; budget gate is the backstop) | `NullRunBackendError` (warn-logged) |
| Gateway unreachable, aggregate rate limit | **Fail-CLOSED** — 503 | `NullRunRateLimitRedisError` |
| Workflow killed via dashboard | Raise at next `/gate` call (or at WS push receipt) | `WorkflowKilledInterrupt` (`BaseException`) |
| Workflow paused via dashboard | Raise at next `/gate` call | `WorkflowPausedException` |
| Missing `api_key` on `init()` | Raise at first SDK call | `NullRunAuthenticationError` |
| HMAC signature missing / stale | Reject the request (401) | `NullRunAuthenticationError` |
| Plan monthly / per-dimension cap reached | Reject the request (422 `plan_limit_exceeded`; `details.resource` names the dimension) | `NullRunBlockedException` (HTTP 422 via `exc.status_code`) |
| Consume over-budget on commit | Reject the `/track` commit (422; actual cost > reserved + ε) | `NullRunConsumeOverbudgetError` |
| Per-minute rate cap reached | Reject the request (429 with `Retry-After`) | `RateLimitError` |
| Chain expired (`max_chain_duration_seconds` exceeded) | 402 | `NullRunChainError` |
| Protocol version too old | 400 | `NullRunProtocolError` |

> Critical paths refuse to run when the gateway is unreachable;
> secondary signals may let calls through.

## What happens when the NullRun service is unavailable

NullRun's service is the gateway that evaluates every `/check` and
`/track` call. When it's down, behaviour is intentionally asymmetric:
**enforcement paths fail-CLOSED** (the safest choice — never let a
tool run that should have been blocked), while **secondary signals**
(per-key rate limits, cost-event outbox writes, dashboard reads) may
fail-OPEN or be queued, because blocking on them would lose data
without protecting the budget.

This table describes every surface that can be affected. If a row
isn't here, the surface behaves as documented in its own concept
page.

| Surface | What you observe during an outage | How to handle it |
| --- | --- | --- |
| **Active `/check` — budget gate** | Fail-CLOSED. SDK raises `NullRunBackendError`; the next `@protect`-wrapped call is refused. No implicit re-reserve. The reservation TTL eventually releases the cents. | Catch the exception; retry with exponential backoff. Long outages will exceed your tool timeout. The budget counter is never decremented by a call the gate never approved. |
| **Active `/check` — sensitive-tool gate** | Fail-CLOSED. The sensitive tool body never runs. SDK raises `NullRunBackendError`. | Treat as **indeterminate** — don't retry the side-effect blindly. Surface the error to the user and let a human decide. This is the canonical reason `@sensitive` is the default for irreversible actions. |
| **Active `/check` — per-key rate limit** | Fail-OPEN (secondary signal). SDK warns and the call proceeds. The budget gate remains the backstop. | No action required. The budget gate still applies on the next call. |
| **Active `/check` — aggregate (per-org) rate limit** | Fail-CLOSED — 503 `NullRunRateLimitRedisError`. | Back off and retry with jitter. This is a true outage of the aggregator, not a transient blip. |
| **Active `/track` — cost commit** | Returns 200 with the cost event queued in the SDK's local outbox. The inference already happened; blocking would lose the cost record. | None required. The SDK persists the event locally and the outbox drains when the gateway returns. **No cost record is lost during the outage window.** |
| **Control plane (WebSocket)** | Connection drops. SDK reconnects with exponential backoff. The local snapshot of workflow status (active / paused / killed) survives. | No operator action — reconnect is automatic. Long outages mean no live kill/pause signals reach the SDK; the next `/check` call picks them up server-side. |
| **In-flight approval request** | Held server-side; not surfaced to operators until the gateway returns. The SDK continues to wait for an approval decision (subject to your approval timeout). | If your approval timeout is short, expect `NullRunApprovalTimeoutError`. The pending request is preserved server-side and reappears in the approvals inbox once the gateway recovers — operators can still answer it. |
| **Dashboard UI** | Pages return 503; read paths may serve cached fragments where possible. The top banner shows "NullRun is currently unavailable." | Refresh once `GET /health/ready` returns 200. Read-only views (audit log, dashboards) resume first; writes (kill, approve, edit) resume once the gateway is fully ready. |
| **HTTP API (programmatic)** | 502 / 503 / 504 on read and write paths. Writes are rejected — the server has no record of success, so there is no implicit retry. | Idempotent reads (`GET`) can be retried freely. Writes (`POST /kill`, `POST /approve`) should not be retried blindly — gate them behind your own idempotency keys if your client retries. |
| **Cost-event outbox (reconciliation)** | Events queue in Redis; the drain loop resumes when the gateway returns. | None — reconciliation is automatic. The outbox catches up on the next gateway tick. Provisional reservations eventually reconcile to final `cost_events` rows. |
| **Alerts & notifications** | Rule evaluation pauses (the gateway can't see new events to score). Outbound delivery depends on channel: Slack messages buffer at Slack's edge; email and webhook channels drop. | Check the channel after recovery. Slack messages sent during the outage arrive late but are not lost; webhook deliveries need a replay tool. See [Notifications](concepts/notifications.md). |
| **Configured workflows, policies, MCP servers, API keys** | Read-only. Nothing can be created, edited, killed, or revoked until the gateway returns. **Already-active rules continue to enforce** on the next gate call — the gate caches the merged Effective Policy. | Plan configuration changes outside the outage window. Operators can still read existing state from cached dashboard fragments. |
| **`GET /health/live`** | Always 200 if the binary is running — even when downstream deps are down. | Use this for liveness probes. **Do not use it as a "is NullRun usable" signal** — it will lie during a Redis or Postgres outage. |
| **`GET /health/ready`** | 200 when DB + Redis + policy cache are reachable; 503 otherwise. | Use this for readiness probes and to page on. This is the signal that flips first as the service recovers. |
| **`GET /api/v1/capabilities`** | 200 with the cached protocol version when the gateway can read from cache; 503 if Redis is unreachable. | Treat 5xx as "stay on the version you already have" — don't auto-upgrade during an outage. The SDK already pins the version it probed at startup. |

### Operator playbook during an outage

1. **Confirm the scope.** Check `GET /health/ready` (or the status
   page). If `/health/ready` is 503 but `/health/live` is 200, the
   gateway process is up but Redis or Postgres is unreachable — every
   enforcement path will fail-CLOSED.
2. **Watch the recovery cascade.** `/health/ready` flips first, then
   `/api/v1/capabilities`, then the WebSocket reconnects, then the
   cost-event outbox finishes draining, then dashboard writes unlock.
   Each layer takes a few seconds; the whole cascade usually finishes
   inside a minute.
3. **Audit the outage window afterwards.** Open the workflow's detail
   page and filter the audit log to the outage window. Every decision
   (including the fail-CLOSED ones) is retained — nothing is lost, and
   the row counts reconcile against the cost-events outbox.
4. **Don't disable the gate to "fix" the outage.** Setting
   `NULLRUN_SKIP_BUDGET_CHECK=1` or `NULLRUN_SENSITIVE_FAIL_OPEN=1`
   bypasses the gate entirely and is unsafe in production. Let the
   gate fail-CLOSED; catch and retry in your code.

## Common runtime questions

### "Why is my call being rejected with `NullRunBlockedException`?"

The most common causes, in order of frequency:

1. **Budget exhausted** — your `policy.budget_cents` ran out, or the
   per-org plan cap (`max_executions_per_month`, `history_days`,
   etc.) was hit. Either raise the cap in the dashboard or wait for
   the next billing cycle.
2. **Tool blocked by ToolBlock policy** — the function name matches
   a glob pattern in an active ToolBlock policy. Inspect the
   merged Effective Policy on the workflow's detail page to see
   which patterns are in scope.
3. **Workflow inactive** — the workflow was soft-deleted, paused,
   or killed. The gate returns 403 `WORKFLOW_INACTIVE` (SDK surfaces as
   `error_code = "NR-W004"`). Restore the workflow from the dashboard
   or create a new one.
4. **Consume over-budget on `/track`** — actual cost exceeded the
   reservation + ε. The gate returns 422 `CONSUME_OVERBUDGET` and
   refuses to commit. Report the actual cost accurately from the
   LLM response.

### "Why is my workflow paused / killed without me doing anything?"

Two usual suspects:

- **Operator action** — open the workflow's detail page; the audit
  log shows the actor and timestamp.
- **Plan or workflow limit** — `max_workflows_per_plan` was hit
  (Lite 5, Starter 25, Growth 150, Scale 500), causing auto-pause.
  Check the plan picker for your tier's cap.

### "Why is the SDK raising `NullRunAuthenticationError`?"

- `NULLRUN_API_KEY` is unset or the key was revoked.
- `NULLRUN_SECRET_KEY` is unset. Set both `NULLRUN_API_KEY` and
  `NULLRUN_SECRET_KEY`.
- The host clock skew between your SDK process and the gateway is
  too large for the HMAC signature window. Sync the host clock.
- The protocol header `X-NULLRUN-PROTOCOL` is missing or below the
  gateway's min_required_version. The SDK auto-probes capabilities
  on first call; upgrade past the min version.

### "Why are some calls tracked and others aren't?"

`@protect` fires on the functions it's wrapped around. Plain
LLM calls (no `@protect`, no auto-instrumented framework) are
**invisible** to NullRun. If you use a framework that the SDK
auto-instruments (see [How-to → LLM frameworks](how-to/llm-frameworks.md)),
you do not need `@protect` to get cost tracking.

## Health endpoints

| Endpoint | Purpose |
| --- | --- |
| `GET /health/live` | Process liveness (always 200 if the binary is running) |
| `GET /health/ready` | Dependency readiness (DB + Redis; 503 if down) |
| `GET /api/v1/capabilities` | Gateway protocol version + feature flags |

## See also

- [Errors → exception hierarchy](reference/errors.md)
- [Concepts → Circuit breaker](concepts/circuit-breaker.md)
- [Concepts → Control plane (WebSocket)](concepts/control-plane.md)
- [Concepts → Budgets](concepts/budgets.md)
- [Reference → HTTP API](reference/http-api.md)
