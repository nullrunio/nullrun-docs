---
title: Error codes
description: NullRun error reference: the gateway error vocabulary, the SDK exception hierarchy, decision versus infrastructure handling, and the full NR-* error-code catalog.
maturity: stable
---

# Error codes

The gateway's error-code registry is the source of truth for what the gateway
can refuse and what HTTP status it answers with. The SDK projects that registry
onto its own catalog: every SDK exception carries an `error_code` such as
`"NR-B004"`, and that value is the user-facing identifier to branch on.

Three vocabularies meet on the wire.

| Vocabulary | Where it appears | Shape |
|---|---|---|
| Gateway `error` slug | The `error` field of a generic API error | `snake_case`, e.g. `rate_limit_exceeded` |
| Gateway `error_code` | The `error_code` field of a gate refusal | `SCREAMING_SNAKE_CASE`, e.g. `BUDGET_HARD_BLOCKED` |
| SDK `error_code` | The `error_code` attribute of an SDK exception | `NR-*`, e.g. `NR-B004` |

A generic API error carries three fields: `error` (the slug), `message` (human
text), and `code` (a `SCREAMING_SNAKE_CASE` companion). Read `error` first.

A gate refusal carries `error_code` (the enforcement code), `error_message`,
and `details` (structured context). The SDK reads the code from the top level
or from inside `details`.

For the three-layer error model — structured exceptions → `on_error` hook →
`format_user_message` and `with nullrun.guard():` — see
[Concepts → Error handling](../concepts/error-handling.md).

## Generic API errors

A generic API error answers with a slug, a message, and a legacy code.

| `error` slug | HTTP | `code` | When |
|---|---|---|---|
| `bad_request` | 400 | `INVALID_INPUT` | Generic invalid input. |
| `invalid_json` | 400 | `INVALID_JSON` | The request body could not be parsed as JSON. |
| `bad_request` | 415 | `INVALID_INPUT` | The request body has no `application/json` content type. |
| `unauthorized` | 401 | `UNAUTHORIZED` | The key is missing, invalid, or expired. |
| `forbidden` | 403 | `FORBIDDEN` | Authenticated, but not allowed. |
| `not_found` | 404 | `NOT_FOUND` | The resource does not exist or is not visible to the caller. |
| `conflict` | 409 | `CONFLICT` | A duplicate, or a race the caller lost. |
| `conflict` | 409 | `APPROVAL_ALREADY_DECIDED` | The approval was already decided. |
| `conflict` | 409 | `APPROVAL_EXPIRED` | The approval expired. |
| `validation_error` | 422 | `VALIDATION_FAILED` | The body parsed but failed schema validation. |
| `validation_error` | 422 | `INVALID_FIELD` | A field in the body has the wrong shape. |
| `plan_limit_exceeded` | 422 | `PLAN_LIMIT_EXCEEDED` | A plan cap was hit. `details.resource` names the dimension. |
| `workflow_limit_reached` | 422 | `WORKFLOW_LIMIT_REACHED` | The active-workflow cap was hit. |
| `rate_limit_exceeded` | 429 | `RATE_LIMIT_EXCEEDED` | A rate cap was hit. The body carries `retry_after`. |
| `internal_error` | 500 | `INTERNAL_ERROR` | A server-side fault. |
| `internal_error` | 503 | `INTERNAL_ERROR` | A dependency was unavailable. The body carries `retry_after`. |
| `not_implemented` | 501 | `NOT_IMPLEMENTED` | The endpoint is not implemented. |

Plan caps all surface as `plan_limit_exceeded`. There is no slug per
dimension — read `details.resource`.

A generic API error becomes `NullRunBackendError` in the SDK, except on these
statuses: `401` and `403` raise `NullRunAuthenticationError`, and `429` raises
`RateLimitError`.

## Gateway wire error codes

A gate refusal carries one of the codes below in `error_code`. The `category`
says what the caller may do about it.

| Category | Meaning |
|---|---|
| `denied` | A rule judged this call unacceptable. Another call may pass, so the model may adapt and try something else. |
| `budget` | A money or quota boundary is exhausted. Stop. Do not retry and do not re-plan. |
| `halt` | The run is over. Retrying, adapting, and waiting all fail the same way. |
| `infra` | A system fault. Retry with backoff. |

Only a `denied` refusal is safe to turn into model-readable text. A model told
that its budget is exhausted will go looking for another tool.

The SDK maps a recognised code to a typed exception. An unrecognised code falls
back to the HTTP status.

| `error_code` | HTTP | Category | SDK exception |
|---|---|---|---|
| `WF_BUDGET_EXCEEDS_ORG_BUDGET` | 200 | `budget` | — |
| `BUSINESS_IMPACT_INVALID` | 400 | `infra` | `NullRunBlockedException` |
| `CHAIN_ID_INVALID` | 400 | `infra` | `NullRunChainError` |
| `EXECUTION_ID_MALFORMED` | 400 | `infra` | `NullRunBackendError` |
| `EXECUTION_ID_REQUIRED` | 400 | `infra` | `NullRunBackendError` |
| `INVALID_EXECUTION_ID` | 400 | `infra` | `NullRunBackendError` |
| `MODEL_REQUIRED` | 400 | `infra` | `NullRunBlockedException` |
| `PROTOCOL_HEADER_INVALID` | 400 | `infra` | `NullRunProtocolError` |
| `PROTOCOL_HEADER_REQUIRED` | 400 | `infra` | `NullRunProtocolError` |
| `PROTOCOL_TOO_NEW` | 400 | `infra` | `NullRunProtocolError` |
| `PROTOCOL_TOO_OLD` | 400 | `infra` | `NullRunProtocolError` |
| `VALIDATION_FAILED` | 400 | `infra` | `NullRunBlockedException` |
| `WORKFLOW_ID_BODY_MISMATCH` | 400 | `infra` | `NullRunBackendError` |
| `API_KEY_DISABLED` | 401 | `infra` | `NullRunAuthError` |
| `API_KEY_EXPIRED` | 401 | `infra` | `NullRunAuthError` |
| `API_KEY_INVALID` | 401 | `infra` | `NullRunAuthError` |
| `API_KEY_MALFORMED` | 401 | `infra` | `NullRunAuthError` |
| `API_KEY_MISSING` | 401 | `infra` | `NullRunAuthError` |
| `API_KEY_REVOKED` | 401 | `infra` | `NullRunAuthError` |
| `BUDGET_ANTI_DOS_RESERVED_CAP` | 402 | `budget` | `NullRunBudgetError` |
| `BUDGET_CACHE_EXCEEDED` | 402 | `budget` | `NullRunBudgetError` |
| `BUDGET_HARD_BLOCKED` | 402 | `budget` | `NullRunBudgetError` |
| `BUDGET_ORG_CEILING_BLOCKED` | 402 | `budget` | `NullRunBudgetError` |
| `BUDGET_OVERDRAFT_EXCEEDED` | 402 | `budget` | `NullRunBudgetError` |
| `BUDGET_PERIOD_NOT_STARTED` | 402 | `budget` | `NullRunBudgetError` |
| `BUDGET_RECHECK_FAILED` | 402 | `infra` | `NullRunBudgetRecheckFailedError` |
| `BUDGET_REDIS_UNAVAILABLE` | 402 | `infra` | `NullRunBudgetError` |
| `BUDGET_SOFT_BLOCKED` | 402 | `budget` | `NullRunBudgetError` |
| `BUDGET_WORKFLOW_BLOCKED` | 402 | `budget` | `NullRunBudgetError` |
| `CHAIN_MAX_DURATION_EXCEEDED` | 402 | `halt` | `NullRunChainError` |
| `EXECUTION_QUOTA_EXCEEDED` | 402 | `budget` | `NullRunBlockedException` |
| `RESERVED_SCANNED_PARTIAL` | 402 | `budget` | `NullRunBudgetError` |
| `APPROVAL_DENIED` | 403 | `denied` | `NullRunApprovalDeniedError` |
| `APPROVAL_EXPIRED` | 403 | `denied` | `NullRunApprovalExpiredError` |
| `APPROVAL_NOT_YET_APPROVED` | 403 | `denied` | `NullRunApprovalNotYetApprovedError` |
| `APPROVAL_TOOL_ARGUMENT_MISMATCH` | 403 | `infra` | `NullRunApprovalDigestMismatchError` |
| `APPROVAL_TOOL_ARGUMENT_UNAVAILABLE` | 403 | `infra` | `NullRunApprovalDbUnavailableError` |
| `CHAIN_CROSS_ORG` | 403 | `infra` | `NullRunChainError` |
| `CHAIN_KEY_MISMATCH` | 403 | `infra` | `NullRunChainError` |
| `CHAIN_ORG_MISMATCH` | 403 | `infra` | `NullRunChainError` |
| `CIRCUIT_BREAKER_TRIPPED` | 403 | `halt` | `NullRunBlockedException` |
| `EXECUTION_KEY_MISMATCH` | 403 | `infra` | `NullRunAuthError` |
| `EXECUTION_ORG_MISMATCH` | 403 | `infra` | `NullRunAuthError` |
| `INSUFFICIENT_SCOPE` | 403 | `infra` | `NullRunAuthError` |
| `MCP_APPROVAL_REQUIRED` | 403 | `denied` | `NullRunMcpApprovalRequiredError` |
| `MCP_DEFINITION_DRIFTED` | 403 | `denied` | `NullRunApprovalToolDigestMismatchError` |
| `MCP_DESTRUCTIVE_BLOCKED` | 403 | `denied` | `NullRunMcpDestructiveBlockedError` |
| `MCP_READONLY_BYPASS_BLOCKED` | 403 | `denied` | `NullRunMcpReadonlyBypassBlockedError` |
| `MCP_TOOL_APPROVAL_REQUIRED` | 403 | `denied` | `NullRunMcpApprovalRequiredError` |
| `MCP_TOOL_BLOCKED` | 403 | `denied` | `NullRunToolBlockedError` |
| `MCP_TOOL_DECISION_REQUIRED` | 403 | `denied` | `NullRunMcpApprovalRequiredError` |
| `MCP_TOOL_REMOVED` | 403 | `denied` | `NullRunToolBlockedError` |
| `ORG_MISMATCH` | 403 | `infra` | `NullRunAuthError` |
| `PARENT_EXECUTION_KEY_MISMATCH` | 403 | `infra` | `NullRunChainError` |
| `PARENT_EXECUTION_ORG_MISMATCH` | 403 | `infra` | `NullRunChainError` |
| `TOOL_BLOCKED` | 403 | `denied` | `NullRunToolBlockedError` |
| `WORKFLOW_INACTIVE` | 403 | `halt` | `NullRunWorkflowInactiveError` |
| `WORKFLOW_PAUSED` | 403 | `halt` | `NullRunBlockedException` |
| `APPROVAL_NOT_FOUND` | 404 | `infra` | `NullRunApprovalDbUnavailableError` |
| `CHAIN_NOT_FOUND` | 404 | `halt` | `NullRunChainError` |
| `EXECUTION_NOT_FOUND` | 404 | `infra` | `NullRunExecutionNotFoundError` |
| `PARENT_EXECUTION_NOT_FOUND` | 404 | `infra` | `NullRunChainError` |
| `SUBWORKFLOW_INVOKE_DISABLED` | 404 | `denied` | `NullRunChainError` |
| `APPROVAL_ALREADY_DECIDED` | 409 | `infra` | `NullRunApprovalReplayRejectedError` |
| `APPROVAL_CONFLICT` | 409 | `infra` | `NullRunApprovalDbUnavailableError` |
| `APPROVAL_DIGEST_MISMATCH` | 409 | `infra` | `NullRunApprovalDigestMismatchError` |
| `APPROVAL_REPLAY_REJECTED` | 409 | `infra` | `NullRunApprovalReplayRejectedError` |
| `APPROVAL_TOOL_DIGEST_MISMATCH` | 409 | `infra` | `NullRunApprovalToolDigestMismatchError` |
| `APPROVAL_TOOL_MISMATCH` | 409 | `infra` | `NullRunApprovalToolMismatchError` |
| `CHAIN_ENDED` | 409 | `halt` | `NullRunChainError` |
| `IDEMPOTENCY_CONFLICT` | 409 | `infra` | `NullRunProtocolError` |
| `IDEMPOTENCY_IN_FLIGHT` | 409 | `infra` | `NullRunBackendError` |
| `IDEMPOTENCY_KEY_MISMATCH` | 409 | `infra` | `NullRunProtocolError` |
| `BATCH_TOO_LARGE` | 413 | `infra` | `NullRunBackendError` |
| `CONSUME_OVERBUDGET` | 422 | `budget` | `NullRunConsumeOverbudgetError` |
| `CONTROL_CHARS_IN_FIELD` | 422 | `infra` | `NullRunBackendError` |
| `EXECUTION_NOT_BOUND` | 422 | `infra` | `NullRunExecutionNotFoundError` |
| `LEGACY_GRANT_REJECTED` | 422 | `infra` | `NullRunBlockedException` |
| `WORKFLOW_CYCLE_DETECTED` | 422 | `infra` | `NullRunChainError` |
| `WORKFLOW_DEPTH_EXCEEDED` | 422 | `infra` | `NullRunChainError` |
| `WORKFLOW_PARENT_BINDING_EXPIRED` | 422 | `infra` | `NullRunChainError` |
| `BUDGET_EXCEEDED` | 429 | `budget` | `NullRunBudgetError` |
| `LOOP_DETECTED` | 429 | `denied` | `NullRunBlockedException` |
| `RATE_LIMIT_EXCEEDED` | 429 | `budget` | `RateLimitError` |
| `RATE_LIMIT_PLAN_TIER` | 429 | `budget` | `RateLimitError` |
| `TOO_MANY_PENDING_APPROVALS` | 429 | `budget` | `NullRunBlockedException` |
| `WAITLIST_RATE_LIMITED` | 429 | `denied` | `RateLimitError` |
| `APPROVAL_CREATE_FAILED` | 500 | `infra` | `NullRunApprovalDbUnavailableError` |
| `APPROVAL_DIGEST_RECOMPUTE_FAILED` | 500 | `infra` | `NullRunApprovalDbUnavailableError` |
| `APPROVAL_PERSISTENCE_FAILED` | 500 | `infra` | `NullRunApprovalDbUnavailableError` |
| `APPROVAL_VALIDATION_FAILED` | 500 | `infra` | `NullRunApprovalDbUnavailableError` |
| `EXECUTION_BINDING_MISSING` | 500 | `infra` | `NullRunBackendError` |
| `INTERNAL_ERROR` | 500 | `infra` | `NullRunBackendError` |
| `WORKFLOW_BUDGET_CONFIG_INVALID` | 500 | `infra` | `NullRunBackendError` |
| `APPROVAL_DB_UNAVAILABLE` | 503 | `infra` | `NullRunApprovalDbUnavailableError` |
| `APPROVAL_RULES_UNAVAILABLE` | 503 | `infra` | `NullRunApprovalDbUnavailableError` |
| `AUTH_BACKEND_UNAVAILABLE` | 503 | `infra` | `NullRunBackendError` |
| `BUDGET_DATA_UNAVAILABLE` | 503 | `infra` | `NullRunBackendError` |
| `BUDGET_PROJECTION_UNAVAILABLE` | 503 | `infra` | `NullRunBackendError` |
| `CIRCUIT_BREAKER_STATE_LOOKUP_FAILED` | 503 | `infra` | `NullRunBackendError` |
| `EXECUTION_BINDING_READ_FAILED` | 503 | `infra` | `NullRunBackendError` |
| `EXECUTION_BINDING_WRITE_FAILED` | 503 | `infra` | `NullRunBackendError` |
| `EXECUTION_RESOLVE_REDIS_ERROR` | 503 | `infra` | `NullRunBackendError` |
| `IDEMPOTENCY_REDIS_UNAVAILABLE` | 503 | `infra` | `NullRunBackendError` |
| `INGESTION_BACKPRESSURE` | 503 | `infra` | `NullRunBackendError` |
| `INGESTION_CLOSED` | 503 | `infra` | `NullRunBackendError` |
| `INVOKE_PERSIST_FAILED` | 503 | `infra` | `NullRunBackendError` |
| `MCP_REGISTRY_UNAVAILABLE` | 503 | `infra` | `NullRunBackendError` |
| `ORG_CONTEXT_UNRESOLVED` | 503 | `infra` | `NullRunBackendError` |
| `POLICY_UNCONFIGURED` | 503 | `infra` | `NullRunBlockedException` |
| `RATE_LIMITER_UNAVAILABLE` | 503 | `infra` | `NullRunRateLimitRedisError` |
| `RATE_LIMIT_PLAN_LOOKUP_FAILED` | 503 | `infra` | `NullRunRateLimitRedisError` |
| `RATE_LIMIT_REDIS_UNAVAILABLE` | 503 | `infra` | `NullRunRateLimitRedisError` |
| `REDIS_UNAVAILABLE` | 503 | `infra` | `NullRunBackendError` |
| `RESERVATION_NOT_FOUND` | 503 | `infra` | `NullRunBackendError` |
| `RESERVE_DISABLED` | 503 | `infra` | `NullRunBackendError` |
| `TOOL_BLOCKED_BACKSTOP_UNAVAILABLE` | 503 | `infra` | `NullRunBackendError` |
| `WORKFLOW_DEPTH_LOOKUP_FAILED` | 503 | `infra` | `NullRunChainError` |
| `WORKFLOW_INACTIVE_LOOKUP_FAILED` | 503 | `infra` | `NullRunBackendError` |

Three codes come from the request parser rather than the registry. They answer
on the enforcement path with `error_code` set to `INVALID_JSON` (400),
`INVALID_FIELD` (422), or `MISSING_CONTENT_TYPE` (415).

## SDK exception hierarchy

Every public SDK exception inherits from `NullRunError` and carries four
structured fields: `error_code`, `user_action`, `retryable`, and `docs_url`.

```
Exception
└── BreakerError
    ├── BreakerTransportError           events could not be delivered
    │   └── InsecureTransportError     HTTPS was required
    └── NullRunError
        ├── NullRunDecision                  marker — expected policy outcomes
        │   ├── NullRunBlockedException      NR-X001
        │   │   ├── NullRunDeniedError                        NR-D001
        │   │   ├── NullRunBudgetError                        NR-B004
        │   │   │   └── NullRunBudgetRecheckFailedError        NR-B006
        │   │   ├── NullRunToolBlockedError                   NR-T001
        │   │   ├── NullRunApprovalDbUnavailableError         NR-A016
        │   │   ├── NullRunApprovalResponseMissingError       NR-A004
        │   │   ├── NullRunApprovalNotYetApprovedError        NR-A010
        │   │   ├── NullRunApprovalDeniedError                NR-A011
        │   │   ├── NullRunApprovalExpiredError               NR-A012
        │   │   ├── NullRunApprovalReplayRejectedError        NR-A015
        │   │   ├── NullRunApprovalDigestMismatchError        NR-A013
        │   │   ├── NullRunApprovalToolDigestMismatchError    NR-A014
        │   │   ├── NullRunApprovalToolMismatchError          NR-A017
        │   │   ├── NullRunMcpDestructiveBlockedError         NR-MCP01
        │   │   ├── NullRunMcpReadonlyBypassBlockedError      NR-MCP02
        │   │   └── NullRunMcpApprovalRequiredError           NR-MCP03
        │   ├── NullRunConsumeOverbudgetError                 NR-O001
        │   ├── NullRunChainError                             NR-CH001
        │   ├── WorkflowPausedException                       NR-W003
        │   └── NullRunWorkflowInactiveError                  NR-W004
        ├── WorkflowKilledInterrupt          NR-W002 — not a NullRunDecision
        │   └── NullRunWorkflowKilledError   NR-W002
        └── NullRunInfrastructureError       marker — system failures
            ├── NullRunConfigError                          NR-C000
            ├── NullRunAuthenticationError                  NR-A001
            │   └── NullRunAuthError                        NR-A003
            ├── NullRunProtocolError                        NR-P001
            │   └── NullRunMalformedGateResponseError       NR-P002
            ├── NullRunGateIndeterminateError               NR-P004
            ├── NullRunUnknownActionError                   NR-P005
            ├── NullRunUnclassifiedRefusalError             NR-P003
            ├── NullRunRateLimitRedisError                  NR-R002
            └── NullRunTransportError                       NR-B001
                ├── NullRunBackendError                     NR-B002
                │   └── NullRunExecutionNotFoundError       NR-EX01
                └── RateLimitError                          NR-R001
```

Three classes sit outside the marker split, and each one matters when you
write an `except` chain.

- `WorkflowKilledInterrupt` inherits from `NullRunError` directly, not from
  `NullRunDecision`. A kill is not a policy decision, so
  `except NullRunDecision` does not catch it. Catch it by name.
- `NullRunApprovalDbUnavailableError` inherits from
  `NullRunBlockedException`, so it lands in the decision branch even though an
  unreachable approval store is a system failure. Its `error_code`
  (`NR-A016`) is what distinguishes it.
- `BreakerTransportError` and `InsecureTransportError` inherit from
  `BreakerError`, not from `NullRunError`. `except NullRunError:` does not
  catch them.

`NullRunUnclassifiedRefusalError` lives in the SDK's category module, not the
exception module. It is still importable from the package.

`NullRunBlockedException` carries `.workflow_id`, `.reason`, `.action`,
`.tool_name`, `.status_code`, and `.details`. It has **no** `.message`
attribute — use `str(exc)`.

## Decision vs. infrastructure

The hierarchy splits `NullRunError` into two marker subclasses by what kind of
event the exception represents. The split is additive: every existing
`except NullRunError:` and `except NullRunBlockedException:` clause keeps
matching.

| Marker | What it covers | Why it matters |
|---|---|---|
| `NullRunDecision` | Expected policy outcomes — budget cap, tool block, chain rejection, loop detection, workflow pause, over-budget commit. | The enforcement layer did its job. UX explains the decision and, where it applies, offers an upgrade or an alternative action. |
| `NullRunInfrastructureError` | System failures — network unreachable, gateway 5xx, gateway 429, auth rejection, config error, rate limiter down. | The SDK could not reach or query the policy engine. UX is a generic "service unavailable". Operators triage with `error_code`, `retryable`, and for transport errors `source` and `endpoint`. |

Rate limits land on the infrastructure side. A 429 arrives as `RateLimitError`,
a subclass of `NullRunTransportError` → `NullRunInfrastructureError`. Handle it
as a system failure with a retry, and surface `upgrade_url` when the user
genuinely needs a higher plan.

`WorkflowKilledInterrupt` belongs to neither marker. Catch it by name ahead of
both.

### Recommended handler shape

```python title="decision_vs_infra_handler.py"
import nullrun
from nullrun.breaker.exceptions import (
    NullRunDecision,
    NullRunInfrastructureError,
)

try:
    result = run_the_agent(message)
except NullRunDecision as exc:
    # Expected. Surface it to the user and tag it with the code.
    logger.info("nullrun_decision code=%s", exc.error_code)
    return nullrun.format_user_message(exc)
except NullRunInfrastructureError as exc:
    # System failure. Alert ops and retry with backoff.
    logger.exception("nullrun_infrastructure code=%s", exc.error_code)
    return nullrun.format_user_message(exc)
```

### Mapping decisions to HTTP status

The gateway answers a refusal with its own status. A host that re-exposes the
failure to its own clients picks its own status.

The SDK's FastAPI integration ships one mapping. It keys on the `error_code`,
not on the exception class.

| `error_code` | Status | Meaning |
|---|---|---|
| `NR-B004` | 429 | Budget exhausted. |
| `NR-L001` | 429 | Loop detected. |
| `NR-R001` | 429 | Rate limited. |
| `NR-T001` | 403 | Tool blocked. |
| `NR-X001` | 403 | Generic block. |
| `NR-W003` | 503 | Workflow paused. |
| `NR-W002` | 503 | Workflow killed. |
| any other decision code | 429 | Default for a decision. |
| any infrastructure code | 503 | Default for a system failure. |

`NR-W003` surfaces `resume_after` as the `Retry-After` header. `NR-R001`
surfaces `retry_after` the same way.

`.status_code` carries the gateway's own status on the exceptions that
received one: the `NullRunBlockedException` family,
`NullRunConsumeOverbudgetError`, and `NullRunChainError`. Read it with
`getattr(exc, "status_code", None)` when you need the wire status.

See [Use with FastAPI](../how-to/fastapi.md) for the reference integration.

## HTTP status summary

| Status | Meaning | SDK action |
|---|---|---|
| 200 | OK | — |
| 400 | Bad request | Inspect `message`, fix the request. |
| 401 | Bad API key or signature | Refresh the key, check the signing secret. |
| 402 | Budget refused | Stop. Do not retry. |
| 403 | Forbidden | Check the role, scope, or org. |
| 404 | Not found | The caller handles it. |
| 409 | Conflict | Inspect `message` and `details`. |
| 413 | Body too large | Split the batch. |
| 415 | Unsupported media type | Send `Content-Type: application/json`. |
| 422 | Validation or plan limit | Inspect `details`. |
| 429 | Rate limit | Honour `Retry-After`; check `upgrade_url`. |
| 5xx | Gateway error | Retry with backoff. |

When the gateway is unreachable, the SDK raises `NullRunTransportError` with
`source` set to one of `NETWORK_ERROR`, `GATEWAY_ERROR`, `AUTH_ERROR`, or
`BREAKER_OPEN`.

## NR-* error code catalog

Stable, machine-readable identifiers on every SDK exception.

- **Decision and enforcement codes** — what the gate decided. Surfaced as
  `NullRunDecision` subclasses.
- **Infrastructure codes** — transport, backend, and config failures.
  Surfaced as `NullRunInfrastructureError` subclasses.

`—` in the HTTP column means the SDK raised the error locally, with no wire
status attached.

### Decision and enforcement codes

| `error_code` | When | HTTP | SDK class |
|---|---|---|---|
| `NR-D001` | The operator refused this specific call. Only raised when `init(on_denied="message")` is set. | — | `NullRunDeniedError` |
| `NR-X001` | A policy block with no more specific code. | — | `NullRunBlockedException` |
| `NR-B004` | The workflow budget is exhausted. | 402 | `NullRunBudgetError` |
| `NR-B006` | The budget moved between the gate call and the execute call. | 402 | `NullRunBudgetRecheckFailedError` |
| `NR-L001` | The same tool repeated past the per-policy threshold. | 429 | `NullRunBlockedException` |
| `NR-O001` | The actual cost exceeded the reservation. | 422 | `NullRunConsumeOverbudgetError` |
| `NR-T001` | The tool is in the block list. | 403 | `NullRunToolBlockedError` |
| `NR-T003` | An MCP tool call was blocked by the gate, and the client was not invoked. | — | `NullRunBlockedException` |
| `NR-CH001` | The chain scope check failed — bad chain id, wrong parent, or the max duration exceeded. | 402 or 403 | `NullRunChainError` |
| `NR-EX01` | The execution id is unknown or its binding expired. | 404 | `NullRunExecutionNotFoundError` |
| `NR-W002` | The operator killed the workflow. | — | `NullRunWorkflowKilledError` (alias `WorkflowKilledInterrupt`) |
| `NR-W003` | The workflow is paused. | — | `WorkflowPausedException` |
| `NR-W004` | The workflow is inactive. | 403 | `NullRunWorkflowInactiveError` |
| `NR-A004` | The gate asked for approval and returned no approval id. | — | `NullRunApprovalResponseMissingError` |
| `NR-A010` | The operator has not decided yet. | 403 | `NullRunApprovalNotYetApprovedError` |
| `NR-A011` | The operator denied the approval. | 403 | `NullRunApprovalDeniedError` |
| `NR-A012` | The approval expired. | 403 | `NullRunApprovalExpiredError` |
| `NR-A013` | The action changed since the approval. | 409 | `NullRunApprovalDigestMismatchError` |
| `NR-A014` | The tool surface changed since the approval. | 409 | `NullRunApprovalToolDigestMismatchError` |
| `NR-A015` | The grant was already consumed. | 409 | `NullRunApprovalReplayRejectedError` |
| `NR-A016` | The approval store is unreachable. Fails closed. | 503 | `NullRunApprovalDbUnavailableError` |
| `NR-A017` | The executing tool is outside the approved tool set. | 409 | `NullRunApprovalToolMismatchError` |
| `NR-MCP01` | A destructive MCP tool was blocked. | 403 | `NullRunMcpDestructiveBlockedError` |
| `NR-MCP02` | A read-only MCP tool was blocked. | 403 | `NullRunMcpReadonlyBypassBlockedError` |
| `NR-MCP03` | An MCP tool needs operator approval. | 403 | `NullRunMcpApprovalRequiredError` |

The approval codes are most often seen inside a running agent flow: the SDK
parked for human review, and the operator acted or the grant aged out. Match
the specific subclass first, and fall back to `NullRunBlockedException` when
the exact cause does not matter.

### Infrastructure codes

| `error_code` | When | HTTP | SDK class |
|---|---|---|---|
| `NR-B001` | The request never reached the gateway — timeout, connection error, or DNS failure. | — | `NullRunTransportError` |
| `NR-B002` | The gateway returned 5xx. | 500 or 503 | `NullRunBackendError` |
| `NR-B005` | The SDK's own circuit breaker is open, so the call short-circuits. | 503 | `NullRunBackendError` (with `source=BREAKER_OPEN`) |
| `NR-R001` | The gateway returned 429 with a `Retry-After`. | 429 | `RateLimitError` |
| `NR-R002` | The rate limiter is unavailable. Fails closed. | 503 | `NullRunRateLimitRedisError` |
| `NR-C000` | The SDK is misconfigured. | — | `NullRunConfigError` |
| `NR-C001` | No API key is available — `NULLRUN_API_KEY` is unset and none was passed to `init()`. | — | `NullRunAuthenticationError` |
| `NR-A001` | The credentials were rejected. | 401 or 403 | `NullRunAuthenticationError` |
| `NR-A002` | The key verification answered 200 but carried no organization id. | — | `NullRunAuthenticationError` |
| `NR-A003` | The API key was rejected. | 401 | `NullRunAuthError` |
| `NR-S001` | A development bypass or a removed execution mode was requested. | — | `NullRunConfigError` |
| `NR-P001` | The wire-protocol version does not match the gateway's. | 400 | `NullRunProtocolError` |
| `NR-P002` | The gate response is not a decision the SDK can act on. | — | `NullRunMalformedGateResponseError` |
| `NR-P003` | The refusal carried a category the SDK does not understand, so the SDK cannot tell a policy outcome from a backend fault. | — | `NullRunUnclassifiedRefusalError` |
| `NR-P004` | The SDK could not obtain a decision, and it did not assume one. | — | `NullRunGateIndeterminateError` |
| `NR-P005` | The control plane sent an action type this SDK cannot run. | — | `NullRunUnknownActionError` |
| `NR-T-PARSE` | The gateway response body could not be parsed as JSON. | — | `NullRunTransportError` |

`NR-P003` and `NR-P004` are retryable. `NR-P002` is retryable once the
connection path is fixed. `NR-P001` and `NR-P005` are not.

## See also

- [Concepts → Error handling](../concepts/error-handling.md)
- [SDK API](sdk-api.md)
- [SDK API → User-facing messages](sdk-api.md#user-facing-messages)
- [Use with FastAPI](../how-to/fastapi.md)
- [HTTP API](http-api.md)
- [Circuit breaker](../concepts/circuit-breaker.md)
- [Sensitive tools](../concepts/sensitive-tools.md)
