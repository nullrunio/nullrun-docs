---
title: Troubleshooting
description: Common NullRun questions answered: why is my agent blocked, how to debug a gate decision, what to do when a budget doesn't reset.
---

# Troubleshooting

What to expect when NullRun is doing its job — and how to recover
when it isn't.

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
