# Error codes

The canonical `ApiErrorCode` enum lives in
[`nullrunio/nullrun/contracts/errors.ts`](https://github.com/nullrunio/nullrun/blob/master/contracts/errors.ts)
and is the source of truth. This page maps each code to:

- the SDK exception the Python SDK raises when it sees that error
- the HTTP status code the gateway returns
- when it happens

## Gateway error codes (`error` field on every non-2xx response)

| Code | HTTP | When | SDK exception |
| --- | --- | --- | --- |
| `validation_error` | 400 | Request body / params fail validation | `BreakerError` (with `.details`) |
| `unauthorized` | 401 | Missing or invalid `X-API-Key` / expired session | `NullRunAuthenticationError` |
| `forbidden` | 403 | Key is valid but lacks the required role/scope | `NullRunAuthenticationError` |
| `not_found` | 404 | Workflow / policy / org id does not exist | (no exception — caller handles) |
| `conflict` | 409 | Idempotency conflict / invite already pending | `BreakerError` |
| `unprocessable` | 422 | Request was understood but rejected (e.g. workflow state mismatch) | `BreakerError` |
| `rate_limit_exceeded` | 429 | Too many requests; see `Retry-After` | `RateLimitError` (carries `retry_after`, `upgrade_url`) |
| `execution_limit_exceeded` | 429 | Plan hard cap hit | `RateLimitError` |
| `workflow_limit_reached` | 429 | Plan workflow cap hit | `RateLimitError` |
| `policy_limit_reached` | 429 | Plan policy cap hit | `RateLimitError` |
| `api_key_limit_reached` | 429 | Plan key cap hit | `RateLimitError` |
| `seats_limit_reached` | 429 | Plan seat cap hit | `RateLimitError` |
| `already_member` | 409 | Invite target is already a member | `BreakerError` |
| `invite_already_pending` | 409 | Invite exists for this email | `BreakerError` |
| `cannot_modify_own_role` | 409 | Self-role change blocked | `BreakerError` |
| `cannot_demote_last_owner` | 409 | Org would lose its last owner | `BreakerError` |

> **Phase 0.5:** `trial_limit_exceeded` was removed — NullRun has no
> trial state. Lite plan is permanently free with hard limits.

## SDK exception hierarchy (Python)

Defined in
[`nullrun-sdk-python/src/nullrun/breaker/exceptions.py`](https://github.com/nullrunio/nullrun-sdk-python).

```
BreakerError                          (Exception)
├── NullRunTransportError             (transport failures)
│   ├── RateLimitError                (HTTP 429, carries retry_after)
│   ├── BreakerTransportError
│   │   └── InsecureTransportError
├── NullRunAuthenticationError        (401 / 403)
├── CostLimitExceeded                 (local breaker tripped — not gateway)
├── ApprovalRequired                  (sensitive tool needs approval flow)
├── BreakerTimeout                    (gateway timeout)
├── NullRunBlockedException
│   ├── LoopDetectedException
│   ├── RetryStormException
│   └── RateLimitExceededException    (local loop, not gateway 429)
└── WorkflowPausedException           (paused via control plane)

BaseException
└── WorkflowKilledException
    └── WorkflowKilledInterrupt       (kill via control plane — BaseException
                                       per the kill contract; not Exception)
```

Catch `WorkflowKilledInterrupt` **explicitly and before** any `except
Exception` — it does not subclass `Exception`.

## HTTP status summary

| Status | Meaning | SDK action |
| --- | --- | --- |
| 200 | OK | — |
| 400 | Validation | Inspect `.details`, fix request |
| 401 | Bad API key / HMAC | Refresh key / check `NULLRUN_SECRET_KEY` |
| 403 | Forbidden | Check role / scope |
| 404 | Not found | Caller handles (workflow/policy may have been deleted) |
| 409 | Conflict | Inspect `.message` |
| 422 | Unprocessable | Inspect `.message` (state mismatch) |
| 429 | Rate / plan limit | Honour `Retry-After`; check `upgrade_url` |
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
