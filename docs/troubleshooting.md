---
title: Troubleshooting
maturity: stable
description: Symptom, cause, and fix for the failures a NullRun integration hits: gate refusals, an unreachable gateway, a stalled approval, a budget that does not reset.
---

# Troubleshooting

Format: symptom → cause → fix. If your case is not here, see the
[Errors reference](reference/errors.md), or send a report from the
control center's **Help → Send feedback** form with the `workflow_id` and
the failing decision id.

!!! info "The endpoints that enforce"
    The server answers `410 Gone` on `POST /api/v1/check`, so a client
    that calls `/check` never reaches enforcement. The SDK calls
    **`POST /api/v1/gate`** for the budget and **`POST /api/v1/execute`**
    for the tool policy. Both refuse the call when a rule says no.

## The gate refused the call

Every row below is a decision the gateway made. The wire code is in
the response body, and the SDK raises the exception in the last
column.

| Symptom | Wire code | Status | SDK exception | Fix |
|---|---|---|---|---|
| The workflow ran out of budget | `BUDGET_HARD_BLOCKED` | `402` | `NullRunBudgetError` | Raise the budget in the control center, or wait for the next billing period. |
| The organization's ceiling was reached | `BUDGET_ORG_CEILING_BLOCKED` | `402` | `NullRunBudgetError` | Raise the plan ceiling, or lower the workflow budgets under it. |
| The call cost more than its reservation | `CONSUME_OVERBUDGET` | `422` | `NullRunConsumeOverbudgetError` | Report the real cost. A cost above the reservation plus the tolerance is refused. |
| A tool matches a block pattern | `TOOL_BLOCKED` | `403` | `NullRunToolBlockedError` | Change the pattern, or use a different tool. |
| An MCP tool is destructive | `MCP_DESTRUCTIVE_BLOCKED` | `403` | `NullRunMcpDestructiveBlockedError` | The tool is off limits for this workflow. |
| The plan's executions quota is spent | `EXECUTION_QUOTA_EXCEEDED` | `402` | `NullRunBlockedException` | Raise the plan, or wait for the quota to reset. |
| The workflow is not running | `WORKFLOW_INACTIVE` | `403` | `NullRunWorkflowInactiveError` | Restore the workflow in the control center, or create a new one. |
| The workflow is paused | `WORKFLOW_PAUSED` | `403` | `NullRunBlockedException` | Resume it in the control center. |
| A policy rate limit was hit | `RATE_LIMIT_EXCEEDED` | `429` | `RateLimitError` | Back off. The window is fixed, not sliding. |
| The plan's aggregate cap was hit | `RATE_LIMIT_PLAN_TIER` | `429` | `RateLimitError` | Raise the plan. The cap belongs to the plan, not to your policy. |
| Too many approvals are waiting | `TOO_MANY_PENDING_APPROVALS` | `429` | `NullRunBlockedException` | Clear the backlog in the Approvals view. The cap is 50 per organization. |
| The chain ran past its duration | `CHAIN_MAX_DURATION_EXCEEDED` | `402` | `NullRunChainError` | Start a new chain. The gateway ends a chain after one hour. |
| The request used a stale protocol version | `PROTOCOL_TOO_OLD` | `400` | `NullRunProtocolError` | Upgrade the SDK. It sends version 4. |
| The key is revoked, expired, or disabled | `API_KEY_REVOKED`, `API_KEY_EXPIRED`, `API_KEY_INVALID` | `401` | `NullRunAuthError` | Rotate the key in the control center. |

### The refusal is the wrong one

**The tool name does not match the pattern you wrote.** Matching is
case-sensitive and reads the tool name only. A pattern of
`stripe.*` matches `stripe` and `stripe.charge`, and it does not
match `stripe_charge`. Use `stripe*`. See
[Tool catalog → Pattern syntax](reference/llm-tool-catalog.md#pattern-syntax).

**The approval says the digest does not match.** The approval is bound
to the exact payload it approved. If the arguments changed, the
binding is broken, and the call is refused with
`APPROVAL_DIGEST_MISMATCH`. Send the payload that was approved.

**The approval says the tool does not match.** An approval covers the
tools it was granted for. Running a different tool under that grant is
refused with `APPROVAL_TOOL_MISMATCH`.

## The gateway cannot be reached

Two different failures look alike from the outside. The distinction
matters, because one is a transport fault and the other is a policy
refusal.

| Symptom | Cause | SDK exception | Fix |
|---|---|---|---|
| `NullRunTransportError` right after `init()` | The gateway did not answer the authentication handshake (`POST /api/v1/auth/verify`). | `NullRunTransportError` (NR-B001) | Check the gateway URL and the network. |
| `NullRunBackendError` with a `5xx` status | The gateway answered and reported a fault. | `NullRunBackendError` (NR-B002) | Read the wire code in `details.error_code` and follow its runbook. |
| `NullRunRateLimitRedisError` | The aggregate per-organization rate limiter could not read its counter. The refusal is `503` `RATE_LIMIT_REDIS_UNAVAILABLE`. | `NullRunRateLimitRedisError` (NR-R002) | Back off and retry with jitter. |
| `NullRunBudgetError` with a `402` and `BUDGET_REDIS_UNAVAILABLE` | The budget store was unreachable. The refusal is fail-closed. | `NullRunBudgetError` | Wait for the store to recover. Do not retry the side effect blindly. |
| `NullRunAuthenticationError` or `NullRunAuthError` | The key is missing, rejected, expired, or disabled. | `NullRunAuthenticationError` (NR-A001), `NullRunAuthError` (NR-A003) | See the authentication section. |
| `BreakerTransportError` during a run | The SDK's circuit breaker is open. It watches the event flush, not the gate, and opens after 10 consecutive failed flushes. | `BreakerTransportError` | Wait 30 seconds, then check the gateway. Pending events stay on disk. |

The circuit breaker is the one component that fails open. It fails open
locally: an unreachable gateway short-circuits the event flush inside
your process instead of hanging. The enforcement path itself never
fails open. A missing tool-block answer, a missing rate-limit answer,
or a missing budget answer refuses the call. See
[Circuit breaker](concepts/circuit-breaker.md).

### Do not disable the gate to survive an outage

`NULLRUN_SKIP_BUDGET_CHECK` and `NULLRUN_SENSITIVE_FAIL_OPEN` are
development opt-outs. Each one also needs a second opt-in, and the
sensitive-tool set is empty by default. Neither belongs in a
production deployment. Catch the exception and retry in your code.

## The approval never arrives

| Symptom | Cause | SDK exception | Fix |
|---|---|---|---|
| The wait ended with nothing decided | Nobody answered inside the approval window. The default is 300 seconds, and the SDK clamps the value to between 1 and 3600 seconds. | `NullRunApprovalExpiredError` (NR-A012) | Raise the timeout, or ask a human to answer sooner. |
| The approval was declined | An operator said no. | `NullRunApprovalDeniedError` (NR-A011) | The refusal is final for that payload. Do not retry it. |
| The approval is still pending | The decision has not been made yet. | `NullRunApprovalNotYetApprovedError` (NR-A010) | Wait, or ask the operator. |
| The grant was already used | The same approval was presented twice. | `NullRunApprovalReplayRejectedError` (NR-A015) | Request a fresh approval. |

The approval wait is bounded by
`NULLRUN_APPROVAL_TIMEOUT_SECONDS`. A pending approval stays on the
server through a gateway outage, so it reappears in the Approvals view
once the gateway recovers.

## The call is rejected with `NullRunBlockedException`

The base class covers every refusal that has no more specific class.
Read `exc.status_code` and `exc.details` to find the reason, then
match the wire code against the
[gate refusal table](#the-gate-refused-the-call).

One extra pointer: the workflow's detail page lists the merged
policies in scope, so a tool block can be traced to the rule that
produced it. See [Workflow context](concepts/workflow.md) for the
workflow states a refusal can name.

## The workflow paused or killed on its own

- **An operator acted.** The workflow's audit log shows the actor and
  the timestamp.
- **A plan cap was reached.** The plan limits the number of live
  workflows. The per-tier table is in
  [Performance & limits → Per-plan limits](operations/performance.md#per-plan-limits).

## The SDK raises `NullRunAuthenticationError`

- `NULLRUN_API_KEY` is unset or empty. `init()` reports this with
  error code `NR-C001`.
- The key was revoked, expired, or disabled. The gateway answers `401`
  with the specific code, and the SDK raises `NullRunAuthError`.
- The host clock is too far from the gateway's clock for the signed
  request window. Sync the clock.
- The protocol version is outside the range the gateway supports. The
  SDK sends version 4, and a gateway that answers `PROTOCOL_TOO_OLD`
  does not accept it.

## The SDK raises `ValueError` for the chain id

A chain id must be a UUID v4. The SDK validates the format, the
canonical structure, and the version, and rejects anything else with
a `ValueError`. The `chain()` context manager also takes an
operation, and the valid values are `start`, `continue`, `end`, and
`auto`.

```python
import uuid

import nullrun

with nullrun.chain(str(uuid.uuid4()), op="start"):
    ...
```

## Some calls are tracked and others are not

`@protect` fires on the functions it wraps. A plain model call with
no `@protect` and no auto-instrumented framework is invisible to
NullRun. The SDK instruments these clients on its own, so a model call
made through one of them is tracked without a decorator: `httpx`,
`requests`, LangChain, LangGraph, the OpenAI Agents SDK, LlamaIndex,
CrewAI and AutoGen. See [LLM frameworks](how-to/llm-frameworks.md).

## Health endpoints

| Endpoint | Purpose |
|---|---|
| `GET /health/live` | Process liveness. It answers 200 while the binary runs, even when a dependency is down. Do not use it as a readiness signal. |
| `GET /health/ready` | Dependency readiness. It answers 503 when the database or the budget store is unreachable. This is the signal to page on. |
| `GET /health/startup` | Bootstrap readiness. It answers `started` once migrations and seeds are done. |
| `GET /api/v1/capabilities` | The protocol version range, the live feature flags, and the server version. |

During an outage, `/health/ready` flips first, then the capability
probe answers, then the control-plane WebSocket reconnects, then the
cost-event outbox finishes draining.

## See also

- [Errors reference](reference/errors.md) — the exception hierarchy
- [Circuit breaker](concepts/circuit-breaker.md)
- [Control plane](concepts/control-plane.md)
- [Budgets](concepts/budgets.md)
- [HTTP API](reference/http-api.md)
