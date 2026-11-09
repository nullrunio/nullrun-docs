---
title: Performance & limits
maturity: stable
description: The bounds that affect a NullRun integration — request and approval timeouts, rate limits, per-plan caps, and what happens when the gateway is unreachable.
---

# Performance & limits

The bounds a NullRun integration runs inside. Every number here is
enforced in code, not a target.

## Timeouts

| Bound | Value | Set by |
| --- | --- | --- |
| One gateway request | **30 s** | The SDK, via `NULLRUN_REQUEST_TIMEOUT` |
| Gate handler | **5 s** | The gateway |
| Gate evaluation | **3 s** | The gateway |
| Waiting for an approval | **300 s** by default, between 1 s and 3 600 s | The SDK, via `NULLRUN_APPROVAL_TIMEOUT_SECONDS`, clamped |
| A reservation lives for | **300 s** by default. An approval rule with a deadline extends it to that deadline plus 30 s, and the ceiling is 24 h. | The gateway |

The 3 s evaluation cap is the binding one. The 5 s handler cap is a
safety net above it, and the 30 s request cap is the outermost bound.

Two consequences worth planning around:

- A tool call that runs longer than the reservation lifetime loses
  its reservation. The cost that follows is refused, so budget the
  tool's runtime against the reservation, not against the budget.
- An approval that no human answers inside the window fails. The
  exception is `NullRunApprovalExpiredError`.

## Rate limits

### By address and account

| Limit | Value | Response |
| --- | --- | --- |
| Per IP address | **60 requests per minute**, burst 60 | `429` with `Retry-After` |
| Auth endpoints, per IP | **5 attempts per minute** | `429` |
| One email address | **5 consecutive failures** → 300 s lockout | `429` with `Retry-After` |

### By policy

| Limit | Value | Response |
| --- | --- | --- |
| Per organization and API key | The rate-limit policy's `limit`, counted over the policy's own window. A fixed window, not a sliding one. | `429` `RATE_LIMIT_EXCEEDED` |
| Per organization | The plan's aggregate cap, in requests per minute | `429` `RATE_LIMIT_PLAN_TIER` |

An explicit `RateLimit` policy wins over the plan tier. A policy that
asks for more than the plan allows is clamped down to the plan's cap,
and the clamp is reported in `details.clamped_from_rpm`.

### The plan's aggregate cap

| Plan | Requests per minute, per organization |
| --- | --- |
| Lite | 10 000 |
| Starter | 50 000 |
| Growth | 200 000 |
| Scale | 1 000 000 |
| Enterprise | unlimited |

## Per-plan limits

| Plan | Workflows | Tokens per hour | Executions per month | Requests per second | API keys | Seats | Policies |
|---|---|---|---|---|---|---|---|
| **Lite** | 3 | 10 000 | 75 000 | 5 | 10 | 1 | 3 |
| **Starter** | 8 | 25 000 | 100 000 | 10 | 15 | 3 | 10 |
| **Growth** | 50 | 300 000 | 750 000 | 50 | 100 | 10 | 25 |
| **Scale** | 200 | unlimited | 2 000 000 | 300 | 350 | 75 | 150 |
| **Enterprise** | unlimited | unlimited | unlimited | unlimited | unlimited | unlimited | unlimited |

Approval rules need a plan that includes approvals. Lite and Starter
do not include it, so the create call is refused with `403`
`feature_not_available`. Every other plan carries an approval-rule
quota alongside its policy quota.

## When the gateway is unreachable

The SDK ships a circuit breaker in front of every gateway call. It is
the one component in the chain that fails open, and it fails open
locally: the call is short-circuited inside your process, so a gateway
outage does not turn into a hang.

| Setting | Value |
| --- | --- |
| Consecutive failures before the breaker opens | **5** |
| How long the breaker stays open | **30 s** |
| Probe calls allowed while half-open | **1** |

A call that the breaker short-circuits raises
`NullRunTransportError`. A call that reaches the gateway and gets a
refusal raises the refusal's own exception. The two are different
outcomes and only one of them is a policy decision.

The enforcement path itself never fails open. Every signal below is
required, and a missing signal refuses the call.

| Missing signal | Response |
| --- | --- |
| The tool-block answer | `403` `TOOL_BLOCKED` |
| The aggregate rate-limit answer | `503` `RATE_LIMIT_REDIS_UNAVAILABLE` |
| The budget answer | `402` `BUDGET_REDIS_UNAVAILABLE` |
| The protocol header | `400` `PROTOCOL_HEADER_REQUIRED` |
| The state store, on the cost-tracking path | `200`, retried in the background |

The last row is the only exception. The cost event is written after
the inference has already happened, so the gateway acknowledges the
call and retries the write. The spend is not lost.

## What a refusal looks like

| Situation | Status | Code |
| --- | --- | --- |
| The workflow's budget is exhausted | `402` | `BUDGET_HARD_BLOCKED` |
| The organization's ceiling is reached | `402` | `BUDGET_ORG_CEILING_BLOCKED` |
| The call costs more than its reservation | `422` | `CONSUME_OVERBUDGET` |
| A tool matches a block pattern | `403` | `TOOL_BLOCKED` |
| A policy's rate limit is hit | `429` | `RATE_LIMIT_EXCEEDED` |
| The plan's aggregate cap is hit | `429` | `RATE_LIMIT_PLAN_TIER` |
| Too many approvals are waiting | `429` | `TOO_MANY_PENDING_APPROVALS` |
| The workflow was paused from the dashboard | `403` | `WORKFLOW_PAUSED` |

A consume may exceed its reservation by a small fixed tolerance —
1¢ by default. A larger overshoot is refused with
`CONSUME_OVERBUDGET`.

The per-organization pending-approval cap is **50** by default. A 51st
waiting approval is refused with `TOO_MANY_PENDING_APPROVALS`, and the
caller gets a `429`.

## Gaps

The things we have not measured, stated plainly.

### Not measured

- Real p99 latency to the budget store at production scale, on the
  worst-case reservation path.
- First-request latency during a budget-store partition, before the
  gateway's own breaker trips.
- Write throughput for the cost-event store under a tracking burst.
- Reconnect behaviour for the control-plane WebSocket under a
  split-brain. The gateway puts no cap on it.

### Known limits

- The gateway does not set a timeout on the outbound provider call it
  makes. The 30 s request cap is the only bound.
- The gateway does not retry a failed gate or cost-tracking request.
  The refusal reaches you, and the retry is yours.
- The retry loops in the background workers use a fixed backoff with
  no jitter.
- `Retry-After` is a body field on the gate path. The HTTP header is
  only set by the per-IP limiter.
- The published OpenAPI contract carries fewer response fields than
  the gateway returns. The running gateway is the wire truth.

## See also

- [Circuit breaker](../concepts/circuit-breaker.md) — what the agent
  sees when a failure occurs
- [Error handling](../concepts/error-handling.md) — wire code to
  exception mapping
- [Budgets](../concepts/budgets.md) — reserve and consume semantics
- [API keys](../concepts/api-keys.md) — signing, rotation, drain
- [Control plane](../concepts/control-plane.md) — WebSocket keepalive
- [HTTP API](../reference/http-api.md) — endpoints and the protocol
  version
- [Compliance](../compliance/index.md) — data-handling posture
