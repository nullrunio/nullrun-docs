# Error codes

The canonical `ApiErrorCode` enum is the source of truth for every
non-2xx response the gateway returns. This page maps each code to:

- the SDK exception the Python SDK raises when it sees that error
- the HTTP status code the gateway returns
- when it happens

## Gateway error codes (`error` field on every non-2xx response)

The canonical catalog is `ErrorSlug` in
`backend/src/proxy/http/errors.rs`. The `error` slug is the stable,
machine-readable identifier; `message` is human-safe; `code` is a
legacy SCREAMING_SNAKE_CASE alias kept for backward compatibility.

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

Defined in
[`nullrun-sdk-python/src/nullrun/breaker/exceptions.py`](https://github.com/nullrunio/nullrun-sdk-python).
Every public SDK exception inherits from `NullRunError` and carries
four structured fields: `error_code` (e.g. `"NR-B004"`), `user_action`
(imperative hint), `retryable` (bool), `docs_url`.

```
BreakerError                          (Exception)
├── NullRunError                      (structured base — every field above)
│   ├── NullRunConfigError            (misconfiguration, e.g. missing api_key)
│   ├── NullRunAuthenticationError    (401 / 403)
│   │   └── NullRunAuthError          (401 specifically — NR-A003)
│   ├── NullRunTransportError         (transport failures)
│   │   ├── NullRunBackendError       (5xx — retryable, NR-B002)
│   │   └── RateLimitError            (429 — carries .retry_after, .upgrade_url)
│   ├── NullRunBlockedException       (policy / budget / loop / sensitive block)
│   │   ├── NullRunBudgetError        (budget exhausted — NR-B004)
│   │   └── NullRunToolBlockedError   (tool in block list — NR-T001)
│   └── WorkflowPausedException       (paused via control plane — NR-W003)
└── BreakerTransportError
    └── InsecureTransportError        (HTTP used where HTTPS required)

BaseException
└── WorkflowKilledException           (NR-W002 — parent; emits DeprecationWarning on construction)
    └── WorkflowKilledInterrupt       (kill via control plane — BaseException,
                                       not Exception; per the kill contract)
```

`NullRunBlockedException` carries `.workflow_id`, `.reason`, `.action`
(`"block"` / `"kill"` / `"pause"`), `.tool_name` (when the block is
tool-scoped), and `.details` (free-form). There is **no** `.message`
attribute — use `str(exc)`.

Removed in SDK 0.4.0: `CostLimitExceeded`, `ApprovalRequired`,
`BreakerTimeout`, `LoopDetectedException`, `RetryStormException`,
`RateLimitExceededException` (no remaining callers — see the
`Sprint 2.2` note in `exceptions.py`).

Catch `WorkflowKilledInterrupt` **explicitly and before** any `except
Exception` — it does not subclass `Exception`.

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

- [SDK API](sdk-api.md)
- [HTTP API](http-api.md)
- [Circuit breaker](../concepts/circuit-breaker.md)
- [Sensitive tools](../concepts/sensitive-tools.md)
