# Error codes

The canonical `ApiErrorCode` enum is the source of truth for every
non-2xx response the gateway returns. This page maps each code to:

- the SDK exception the Python SDK raises when it sees that error
- the HTTP status code the gateway returns
- when it happens

For the **three-layer error model** (structured exceptions →
`on_error` hook → `format_user_message` / `@guarded`) and the
boundary between developer-facing and end-user-facing wording, see
[Concepts → Error handling](../concepts/error-handling.md).

## Gateway error codes (`error` field on every non-2xx response)

The canonical catalog lives in the gateway. The `error` slug is
the stable, machine-readable identifier; `message` is human-safe;
`code` is a legacy SCREAMING_SNAKE_CASE alias kept for backward
compatibility.

| `error` slug | HTTP | When | SDK exception |
| --- | --- | --- | --- |
| `bad_request` | 400 | Generic 400 — invalid input that isn't a validation failure | `NullRunConfigError` (or `NullRunError`) |
| `unauthorized` | 401 | Missing or invalid `X-API-Key` / expired session / HMAC mismatch | `NullRunAuthenticationError` (`NullRunAuthError` for 401 specifically) |
| `forbidden` | 403 | Authenticated but not allowed (incl. CSRF mismatch, org-mismatch on `/orgs/*`) | `NullRunAuthenticationError` |
| `not_found` | 404 | Resource doesn't exist or isn't visible | (no exception — caller handles) |
| `conflict` | 409 | Idempotency conflict, duplicate, "already a member", "invite already pending", "cannot demote last owner", etc. | `NullRunError` |
| `validation_error` | **422** | Request body / params failed schema validation | `NullRunConfigError` |
| `plan_limit_exceeded` | **422** | Generic plan cap hit (workflows, seats, api_keys). Body `details.resource` carries which dimension. | `NullRunBlockedException` |
| `workflow_limit_reached` | **422** | Workflow-specific active-workflow cap hit | `NullRunBlockedException` |
| `rate_limit_exceeded` | 429 | Per-minute / per-day rate cap. Body carries `retry_after` (seconds). | `RateLimitError` (carries `.retry_after`, `.upgrade_url`) |
| `internal_error` | 500 | Server-side bug | `NullRunBackendError` (retryable) |
| `not_implemented` | 501 | Feature not yet implemented | `NullRunError` |
| (also `internal_error`) | 503 | `ApiError::ServiceUnavailable` — transient downstream failure on an enforcement path. Carries `retry_after`. | `NullRunBackendError` (retryable) |

> **Phase 0.5:** `trial_limit_exceeded` was removed — NullRun has no
> trial state. Lite plan is permanently free with hard limits.
>
> **Plan limit slugs (api_keys / seats / policies / executions)** all
> surface as `plan_limit_exceeded` with `details.resource` set to the
> dimension name (`"api_keys"`, `"seats"`, `"workflows"`, …). There
> is no separate slug per dimension — read `details.resource`.

## SDK exception hierarchy (Python)

Every public SDK exception inherits from `NullRunError` and carries
four structured fields: `error_code` (e.g. `"NR-B004"`), `user_action`
(imperative hint), `retryable` (bool), `docs_url`.

```
BreakerError                          (Exception)
├── NullRunError                      (structured base — every field above)
│   ├── NullRunDecision               (marker — expected policy outcomes)
│   │   ├── NullRunBlockedException   (policy / budget / loop / sensitive block)
│   │   │   ├── NullRunBudgetError    (budget exhausted — NR-B004)
│   │   │   └── NullRunToolBlockedError (tool in block list — NR-T001)
│   │   └── WorkflowPausedException   (paused via control plane — NR-W003)
│   ├── NullRunInfrastructureError    (marker — system failures)
│   │   ├── NullRunConfigError        (misconfiguration, e.g. missing api_key)
│   │   ├── NullRunAuthenticationError (401 / 403)
│   │   │   └── NullRunAuthError      (401 specifically — NR-A003)
│   │   └── NullRunTransportError     (transport failures)
│   │       ├── NullRunBackendError   (5xx — retryable, NR-B002)
│   │       └── RateLimitError        (429 — carries .retry_after, .upgrade_url)
└── BreakerTransportError
    └── InsecureTransportError        (HTTP used where HTTPS required)

BaseException
└── WorkflowKilledException           (NR-W002 — parent; emits DeprecationWarning on construction)
    └── WorkflowKilledInterrupt       (kill via control plane — BaseException,
                                       not Exception; per the kill contract)
```

`NullRunDecision` and `NullRunInfrastructureError` are **marker
classes**, not exception classes themselves. They exist so host code
can `except NullRunDecision` to catch every expected policy outcome
(budget, tool block, pause) and `except NullRunInfrastructureError` to
catch every system failure (transport, backend 5xx, auth rejection,
config error) — see [Decision vs. infrastructure](#decision-vs-infrastructure)
below for the recommended handling pattern.

`NullRunBlockedException` carries `.workflow_id`, `.reason`, `.action`
(`"block"` / `"kill"` / `"pause"`), `.tool_name` (when the block is
tool-scoped), and `.details` (free-form). There is **no** `.message`
attribute — use `str(exc)`.

Removed in SDK 0.4.0: `CostLimitExceeded`, `ApprovalRequired`,
`BreakerTimeout`, `LoopDetectedException`, `RetryStormException`,
`RateLimitExceededException` (no remaining callers).

Catch `WorkflowKilledInterrupt` **explicitly and before** any `except
Exception` — it does not subclass `Exception`.

## The default path: zero lines of error handling

For the common "run an agent and print a friendly message on failure"
case, the three public helpers do the work — no `try/except NullRunError`
required.

```python title="minimal_boilerplate.py"
import nullrun
from nullrun import init_or_die, guarded, protect, shutdown

init_or_die(api_key="nr_live_...")        # exits cleanly if api_key missing

@guarded                                 # catches NullRunError,
@protect                                 # prints catalog wording,
def my_agent(prompt):                    # sys.exit(1)
    return call_llm(prompt)

if __name__ == "__main__":
    try:
        print(my_agent("hello"))
    finally:
        shutdown()
```

| Helper | Catches | For |
|---|---|---|
| `init_or_die(api_key=...)` | `NullRunError` raised by `init()` (typically `NR-C001`) | Startup; one-shot script entry point |
| `@guarded` | Any `NullRunError` raised inside the wrapped function | Standard agent loop |
| `with nullrun.handle():` | Any `NullRunError` raised inside the block | Region of code (e.g. a graph `invoke`) |

All three propagate `WorkflowKilledInterrupt` (`BaseException`)
unchanged and let non-`NullRunError` exceptions surface as honest
tracebacks. For the full design rationale and the boundary between
"what NullRun tells the developer" and "what the developer tells
their end users", see [Concepts → Error handling](../concepts/error-handling.md).

## Decision vs. infrastructure

The public exception hierarchy splits `NullRunError` into two marker
subclasses by **what kind of event** the exception represents. The
split is additive — every existing `except NullRunError:` and
`except NullRunBlockedException:` clause keeps matching. New code can
use the marker classes to write a two-branch handler that captures
the right behaviour for each category.

| Marker | What it covers | Why it matters |
| --- | --- | --- |
| `NullRunDecision` | Expected policy outcomes — budget cap, tool block, loop detection, workflow pause, per-workflow rate limit | The enforcement layer is doing its job. UX explains the decision and (where applicable) offers an upgrade or alternative action. |
| `NullRunInfrastructureError` | System failures — network unreachable, gateway 5xx, auth rejection, config error | The SDK could not reach or query the policy engine. UX is a generic "service unavailable"; operators triage via `error_code`, `retryable`, and for transport errors, `source` / `endpoint`. |

### Recommended handler shape

```python title="decision_vs_infra_handler.py"
import nullrun
from nullrun import (
    NullRunDecision,
    NullRunInfrastructureError,
)

try:
    result = agent.run(message)
except NullRunDecision as d:
    # Expected — surface to the user, log to product analytics,
    # tag the conversation with d.error_code for cohort analysis.
    return d.user_message() if hasattr(d, "user_message") else str(d)
except NullRunInfrastructureError as e:
    # System failure — alert ops, retry with backoff, do NOT
    # surface internal text to the end user. The catalog has a
    # generic message for every infrastructure error code.
    sentry.capture_exception(e)
    return nullrun.format_user_message(e)
except WorkflowKilledInterrupt:
    # Operator kill (BaseException, not Exception) — re-raise
    # unless you are the top of the agent loop.
    raise
```

### Mapping decision subclasses to HTTP

When you build a server-framework integration (FastAPI, aiohttp,
Telegram bot, Slack handler), map each category to the right HTTP
status:

| Category | HTTP status | Notes |
| --- | --- | --- |
| `NullRunDecision` — budget exhausted (`NR-B004`) | `429` (or backend `402`) | Honour `.retry_after` from the `RateLimitError` if set; budget-exhausted `NullRunBudgetError` exposes the same field via `.details.retry_after` |
| `NullRunDecision` — tool blocked (`NR-T001`) | `403` | User did nothing wrong, but the action is forbidden |
| `NullRunDecision` — workflow paused (`NR-W003`) | `503` | Set `Retry-After` from `.resume_after` |
| `NullRunDecision` — consume overbudget (`CONSUME_OVERBUDGET`) | `422` | Subclass `NullRunConsumeOverbudgetError`; actual cost > reservation + ε |
| `NullRunDecision` — chain error (`NR-CH001`) | `409` | Subclass `NullRunChainError`; chain_id mismatch / expired |
| `NullRunDecision` — workflow inactive (`NR-W004`) | `403` | Subclass `NullRunWorkflowInactiveError`; workflow paused or killed in cross-org scenario |
| `NullRunInfrastructureError` — rate-limit Redis (`NR-R002`) | `503` | `NullRunRateLimitRedisError`. **Fail-CLOSED** — do not retry blindly |
| `NullRunInfrastructureError` — protocol too old (`PROTOCOL_TOO_OLD`) | `400` | `NullRunProtocolError`. Carries `.min_required_version`; SDK must be upgraded past `SDK_MIN_VERSION_FOR_V3` |
| `NullRunInfrastructureError` (any other subclass) | `503` | The failure is on our side, not the user's |
| `WorkflowKilledInterrupt` | `503` | Special ASGI middleware required — see [Use with FastAPI](../how-to/fastapi.md) |

Every `NullRunDecision` subclass carries `.status_code` (the wire
HTTP status the backend returned). The FastAPI integration maps
this field to the response status automatically; in custom
integrations read `exc.status_code` rather than hard-coding the
default above.

The NullRun SDK ships a reference FastAPI integration that applies
this mapping for you — see [Use with FastAPI](../how-to/fastapi.md)
for a one-line setup.

## HTTP status summary

| Status | Meaning | SDK action |
| --- | --- | --- |
| 200 | OK | — |
| 400 | Bad request | Inspect `message`, fix request |
| 401 | Bad API key / HMAC | Refresh key / check `NULLRUN_SECRET_KEY` |
| 403 | Forbidden | Check role / scope |
| 404 | Not found | Caller handles (workflow/policy may have been deleted) |
| 409 | Conflict | Inspect `message` (already-member, invite-already-pending, etc.) |
| 422 | Validation / plan limit | Inspect `details` (for plan limits, `details.resource` + `details.current` + `details.limit`) |
| 429 | Rate limit | Honour `Retry-After`; check `upgrade_url` |
| 5xx | Gateway error | Retry with backoff; sensitive tools fail-closed |

When the gateway is unreachable, the SDK raises
`NullRunTransportError` with `source` set to one of `NETWORK_ERROR`,
`GATEWAY_ERROR`, `BREAKER_OPEN`, `AUTH_ERROR`. See ADR-008 for the
full rationale.

## See also

- [Concepts → Error handling](../concepts/error-handling.md) — the
  three-layer model, minimal-boilerplate helpers, dev/end-user boundary
- [SDK API](sdk-api.md)
- [SDK API → User-facing messages](sdk-api.md#user-facing-messages)
- [Use with FastAPI](../how-to/fastapi.md)
- [HTTP API](http-api.md)
- [Circuit breaker](../concepts/circuit-breaker.md)
- [Sensitive tools](../concepts/sensitive-tools.md)
