title: Error handling
maturity: stable
description: The full NullRun exception hierarchy, kill-signal semantics, and the multi-layer fail-CLOSED contract that protects production traffic.
# Error handling

Errors in NullRun come in three layers, designed for three audiences:
your code, your monitoring, and your end users. The SDK does most of
the work — you pick how much of each layer to use.

!!! tip "Quick reference"
    | Audience | Hook / Class | Catches |
    |---|---|---|
    | Your code | `except NullRunDecision` | Expected policy outcomes (budget, tool block, pause) |
    | Your code | `except NullRunInfrastructureError` | Transport / 5xx / auth / config failures |
    | Your code | `except NullRunWorkflowKilledError` (or `WorkflowKilledInterrupt`) | Operator kill — terminal; caught by `except Exception:`, handle explicitly if you need to checkpoint before exit |
    | Your monitoring | `@nullrun.on_error` hook | Every `NullRunError`, fired before propagation |
    | Your end user | `with nullrun.handle():` / `format_user_message` | Friendly text from the catalog |

## Where errors appear in the dashboard

Every error the SDK raises lands in **Governance → Audit log** —
every decision ever recorded, hash-chained and filterable by
workflow, time range, decision type, and tool name. The reason
column shows `BUDGET_HARD_BLOCKED`, `TOOL_BLOCKED`,
`RATE_LIMIT_EXCEEDED`, etc. Useful both for "what just happened?"
and for compliance review / incident forensics.

<figure class="nr-shot">
  <img class="nr-shot__light" src="../../assets/images/screenshots/audit-log-light.png"
       alt="Audit log page listing every gate decision ever made by the org.">
  <img class="nr-shot__dark" src="../../assets/images/screenshots/audit-log-dark.png"
       alt="Audit log page listing every gate decision ever made by the org.">
  <figcaption class="nr-shot__caption">Governance · Audit log</figcaption>
</figure>

The audit log is the source of truth for "did the agent call the
right thing?". Pair it with [Traces](tracing.md) for full context.

## The three layers

| Layer | Who consumes it | What they see | Purpose |
|---|---|---|---|
| **1. Structured exception** | Your Python code | Exception type, error code, what to do next | Your code decides: retry, fail, surface to UI |
| **2. `on_error` hook** | Sentry / Datadog / logs | Same exception + context (workflow, tool, stage) | Observability: you see every error in your existing dashboards |
| **3. `with nullrun.handle():` / `format_user_message`** | End user | One friendly sentence from a catalog | The user gets a clean message, not a stack trace |

The SDK ships all three. You decide how much to use.

## Layer 1 — the structured exception

Every NullRun exception carries four fields your code can branch on:

| Field | What it is | Example |
|---|---|---|
| `error_code` | Stable machine-readable identifier | `NR-B004`, `NR-R001`, `NR-T001` |
| `user_action` | What to do next | `Wait 30s, then retry` |
| `retryable` | True if retry-after-backoff makes sense | True for rate limit, False for budget |
| `docs_url` | URL to the per-code docs page | `https://docs.nullrun.io/reference/errors#sdk-exception-hierarchy-python` |

The full catalog lives in that reference page; the standard set is:

- `NR-B004` — workflow budget exhausted
- `NR-B002` — gateway 5xx
- `NR-B006` — post-approval budget re-check failed on the same envelope as the original `/gate`. The SDK raises `NullRunBudgetRecheckFailedError`. Operator must re-approve or the workflow can no longer run.
- `NR-R001` — per-workflow rate limit
- `NR-R002` — rate-limit Redis unavailable
- `NR-T001` — tool block list hit
- `NR-CH001` — chain context invalid
- `NR-W004` — workflow soft-deleted or killed
- `NR-A003` — API key rejected
- `NR-A010` — approval row exists, status `PENDING` — operator has not decided yet
- `NR-A011` — operator explicitly denied the approval — terminal, request a fresh grant
- `NR-A012` — approval expired (`expires_at` is in the past)
- `NR-A013` — business-impact digest drifted since operator approval — re-approval required
- `NR-A014` — capability digest drifted (silent capability-gain attack surface) — re-approval required
- `NR-A015` — grant already consumed by a prior `/execute` (replay rejected)
- `NR-P001` — wire-protocol version mismatch
- `NR-O001` — actual cost > reservation + ε (HTTP 422)
- `NR-X001` — generic catch-all raised when a policy block matches a code the SDK does not have a dedicated class for. Match on `NullRunBlockedException` and read `.error_code` if you want specific handling.

For the exception classes used to surface these codes, see
[Reference → Errors → SDK exception hierarchy](../reference/errors.md#sdk-exception-hierarchy-python).

The wire code is still available via the response body or `.status_code`
when you need it for metrics / dashboards.

You catch a specific exception type and inspect the fields:

```python
from nullrun.breaker.exceptions import RateLimitError

@nullrun.protect
def my_agent(prompt):
    try:
        return call_llm(prompt)
    except RateLimitError as exc:
        # exc.error_code = "NR-R001"
        # exc.retryable = True
        # exc.retry_after = 30  (seconds)
        # exc.upgrade_url = "..."  (link to upgrade plan)
        time.sleep(exc.retry_after)
        return call_llm(prompt)
```

For most cases you don't need to import specific types — catching
the parent `NullRunError` and reading `error_code` is enough.

## Layer 2 — the `on_error` hook

For Sentry / Datadog / your log aggregator, register a hook that fires
for every `NullRunError` **before** it propagates:

```python
import nullrun
import sentry_sdk

@nullrun.on_error
def _to_sentry(err, ctx):
    sentry_sdk.capture_exception(err, extra={
        "code": err.error_code,
        "retryable": err.retryable,
        "stage": ctx.stage,
        "workflow_id": ctx.workflow_id,
        "tool_name": ctx.tool_name,
    })
```

The hook fires **once per error**, in registration order. Hook
exceptions are caught and logged at DEBUG — a misbehaving Sentry
can't break your agent.

The context object (`ctx`) carries: `stage` (init / transport /
track / gate), `workflow_id`, `tool_name`, `api_key_prefix` (first
12 chars of the API key, never the full value), `correlation_id`
(per-request UUID), `timestamp`, `extra` (vendor-specific dict).

Multiple hooks are supported:

```python
@nullrun.on_error
def _to_sentry(err, ctx): ...

@nullrun.on_error
def _to_log(err, ctx):
    log.warning("NullRun error", extra={"code": err.error_code})
```

The hook fires for every `NullRunError` subclass — **including the
kill signal** (`WorkflowKilledInterrupt` and its typed alias
`NullRunWorkflowKilledError`). If you want to skip kill inside the
hook, filter on `error_code` (`"NR-W002"`).

## Layer 3 — `with nullrun.handle():` and `format_user_message`

For scripts that just want "run the agent and print a friendly
message on failure", use the no-boilerplate helpers. The first
`@protect` call lazily creates the runtime:

```python
from nullrun import protect, shutdown

@protect
def my_agent(prompt):
    return call_llm(prompt)


if __name__ == "__main__":
    try:
        with nullrun.handle():
            print(my_agent("What does NullRun do?"))
    finally:
        shutdown()
```

What your terminal looks like on a rate-limit hit. `handle()` prints
the structured four-line developer report (catalog headline +
`[error_code]` + `what` + `where` + `why` + `how to fix`):

```
$ python my_agent.py
Too many requests. Please wait a moment and try again.
  [NR-R001] what: rate limit (retryable)
           where: endpoint=gate status=429 source=GATEWAY_ERROR
           why: Per-workflow rate limit exceeded; retry after 30s.
           how to fix: Wait 30s, then retry the call.
$ echo $?
1
```

`with nullrun.handle():` catches every `NullRunError` — which now
includes the kill signal (`WorkflowKilledInterrupt` /
`NullRunWorkflowKilledError` both inherit from `NullRunError`) —
prints the structured report to stderr, and exits with code 1. To
handle kill distinctly (for example, checkpoint state before exit),
use the un-`handle()` form and add your own
`except NullRunWorkflowKilledError:` arm.

`handle()` is the recommended form: it gives a clearer scope,
accepts an `exit_code` argument, and the four-line report is what it
always renders. `@guarded` is the decorator equivalent of the same
behaviour.

`handle()` / `guarded()` are for scripts and one-shots. For
long-running services you want explicit handling — see
[Server frameworks](#server-frameworks) below.

### Branded wording

If you want your own error messages (e.g. "You've used all your
support credits" instead of the default wording), call
`set_user_message` once at the top of your entry point (or register
it via `atexit`):

```python
import nullrun

nullrun.set_user_message(
    "NR-B004",
    "You've used all your support credits. Upgrade to keep chatting.",
)
```

Overrides live in a per-process dict. They don't persist across
processes and aren't synced to the gateway — they're presentation
sugar on top of the catalog.

## Server frameworks

For FastAPI / aiohttp / Flask / Django, you don't want `handle()`
(it exits the process). Instead,
catch the exception in your request handler and return an appropriate
HTTP status:

```python
from nullrun import NullRunError

@app.post("/chat")
async def chat(req: ChatRequest):
    try:
        return await run_agent(req.message)
    except NullRunError as exc:
        # Return the catalog wording as the user-facing message,
        # log the structured fields server-side.
        raise HTTPException(
            status_code=exc.status_code or 503,
            detail={"message": nullrun.format_user_message(exc), "code": exc.error_code}
        )
```

The mapping from exception to HTTP status is documented in
[Reference → Errors → Decision subclasses to HTTP](../reference/errors.md#mapping-decision-subclasses-to-http).

## Audit trail

Every decision is recorded in the audit log; you can fetch the full
log via the API. The audit log is the source of truth for "did the
agent call the right thing?". Pair it with [Traces](tracing.md) for
full context.

## What is NOT stored

NullRun never persists:

- **Prompt content** or **LLM response payloads**. The gate
  receives only `model`, `tool`, `tools`, `estimated_tokens`, and
  optional `business_impact` typed payload.
- **Tool arguments** beyond the typed `BusinessImpact` extraction.
  Operators do not write JSONPath rules over tool payloads.
- **MCP interaction payloads** — only the canonical tool name is
  logged.
- **Card numbers, CVC, expiry month/year** — Polar is the
  merchant of record. Subscriptions carry only `payment_method_brand`
  and `payment_method_last4`.
- **OAuth refresh tokens** — the IdP owns session lifetime.

Email addresses and prompts are hashed or redacted at the log and
trace-span boundary so plaintext does not reach the structured log
store. Uppercase `KEY=VALUE` pairs are rewritten to `KEY=[REDACTED]`
before bytes reach stdout.

## Kill signal

The operator kill signal arrives as `WorkflowKilledInterrupt` or its
typed alias `NullRunWorkflowKilledError` (recommended). Both inherit
from `NullRunError`, so a bare `except Exception:` arm catches the
kill alongside every other SDK error:

```python
try:
    my_agent(prompt)
except Exception:
    log.error("agent failed", exc_info=True)
# WorkflowKilledInterrupt IS caught here.
```

If you want kill-specific handling — checkpointing state, notifying
a supervisor, exiting with a clean reason — catch the typed alias
**explicitly** and re-raise it after handling (the kill contract is
"operator's word is final"):

```python
from nullrun import NullRunWorkflowKilledError

try:
    my_agent(prompt)
except NullRunWorkflowKilledError:
    persist_state()
    raise
except NullRunError:
    log.error("agent failed", exc_info=True)
```

`handle()` / `@guarded` catches kill via the standard `NullRunError`
arm — it prints the structured four-line report and exits 1. To keep
the process alive on kill (checkpoint, notify a supervisor, then
exit), use the un-`@guarded` / un-`handle()` `protect()` form with
your own `except NullRunWorkflowKilledError:` arm above.

## See also

- [Reference → Errors](../reference/errors.md) — full catalog
- [Troubleshooting](../troubleshooting.md) — common questions and
  their fixes
- [Use with FastAPI](../how-to/fastapi.md) — exception handling
  inside ASGI handlers
- [Tracing](tracing.md) — how errors map to spans

!!! info "Deep dive"

    Wire codes are minted by
    `backend/src/proxy/http/gate/error_codes.rs` in a single
    `GateErrorCode` enum. The `#[serde(rename_all =
    "SCREAMING_SNAKE_CASE")]` derive guarantees the on-the-wire
    string matches the variant name verbatim (e.g.
    `BudgetHardBlocked` → `"BUDGET_HARD_BLOCKED"`), and the
    `as_str()` match arm is the authoritative source of truth —
    adding a variant is a minor-bump protocol change, renaming is a
    major bump. HTTP status comes from `http_status()` per the
    CLAUDE.md §13 table: money-math (402), security / ownership
    (403), lineage lookup miss (404), rate-limit (429), semantic
    validation (422). Wire envelope shape per `v3_error_envelope`:
    `{error_code, error_message, details, retry_after_ms}`. The
    handler at `gate.rs::gate_response_to_response` routes both
    `/gate` and `/execute` through the same helper so block
    decisions carry their canonical HTTP 4xx status — pre-fix
    `/execute` hardcoded `Json(response).into_response()` (defaults
    to 200) which silently fail-OPEN'd sensitive execute paths to
    SDKs that branch on HTTP status first (httpx `raise_for_status`).
    The kill path: `kill_workflow_handler`
    (`backend/src/proxy/handlers.rs`) → `kill_legacy` →
    `kill_execution` validates the `State::Killed` transition
    (ADR-007), publishes `WorkflowEventPayload::StateChanged` to
    the EventBus, and the WS control plane (`ws_control.rs`) pushes
    `WsMessage::StateChange` with `WsWorkflowState::Killed` to the
    SDK, which raises `WorkflowKilledInterrupt` (alias
    `NullRunWorkflowKilledError`).

    Every gate rejection is fail-CLOSED. The orchestrator at
    `run_gate_orchestrator` runs the steps in priority order
    (`Block > RequireApproval > Allow`, ADR-011 §"Decision priority")
    and short-circuits on the first non-Allow, so the SDK sees a 4xx
    block before any budget envelope is minted. Lua `RESERVE_SCRIPT`
    returns typed 5-tuple diagnostics (`{spent, budget, projected}`)
    so operators can reconstruct the rejection from logs alone
    (ADR-016 §2.4.2). The `RedisCircuitBreaker` /
    `PostgresCircuitBreaker` (ADR-055, shipped 2026-09-21) wrap
    every gate hot-path site, so a Redis or Postgres partition now
    short-circuits sub-100ms (FailClosed / Buffered / Degraded modes
    per `infra::FailureMode`) instead of hanging 5–10s on
    `pool.acquire()`. The kill signal inherits from `NullRunError`,
    so `except Exception:` catches it alongside every other SDK
    error; `handle()` / `@guarded` catch it via the standard
    `NullRunError` arm and print the structured four-line developer
    report.

    Wire codes fall into three buckets: **decision** (block / allow /
    require_approval), **infrastructure** (Redis-down, Postgres-down,
    `BUDGET_REDIS_UNAVAILABLE`, `IDEMPOTENCY_REDIS_UNAVAILABLE`), and
    **transport** (`INVALID_JSON` / `INVALID_FIELD` from JSON
    rejection — DEF-DESTR-RUNNER-HTTP-STATUS). The SDK's
    `exc.error_code` is the stable machine-readable identifier;
    `exc.retryable` and `exc.retry_after` drive the SDK's
    retry/backoff loop. Approval-flow codes (`APPROVAL_NOT_FOUND`,
    `APPROVAL_DENIED`, `APPROVAL_EXPIRED`,
    `APPROVAL_DIGEST_MISMATCH`, `APPROVAL_TOOL_DIGEST_MISMATCH`,
    `APPROVAL_REPLAY_REJECTED`, `APPROVAL_NOT_YET_APPROVED`) all
    share the 403 / 404 buckets with other ownership / auth-family
    codes (DEF-TS99-002). The kill signal flows through the
    WebSocket envelope as `WsWorkflowState::Killed` →
    `WsApprovalOutcome::Denied` (or `Expired`) → SDK raises
    `WorkflowKilledInterrupt`, and the `@nullrun.on_error` hook
    fires once per `NullRunError`, **including the kill signal** —
    filter on `error_code` (`"NR-W002"`) to skip it.

    The `GateErrorCode` enum replaces a prior design where wire
    strings were inline literals at the call site. The enum-backed
    approach lets `gate_response_to_response` resolve HTTP status
    from a single match table; the inline-literal approach silently
    fail-OPEN'd `/execute` block decisions as HTTP 200. Approval-flow
    codes were initially absent from `all()` (DEF-TS99-002,
    2026-09-16) — they existed as inline strings in the orchestrator
    but `gate_response_to_response` couldn't resolve a HTTP status
    and defaulted to 200; adding them to `all()` closed the
    wire-surface gap. The kill signal was originally
    `WorkflowKilledException` (a `BaseException` subclass); the
    0.18.2 SDK removed that class entirely — only
    `NullRunWorkflowKilledError` and its alias
    `WorkflowKilledInterrupt` survive, both inheriting from
    `NullRunError(Exception)`. Idempotency on `/gate` and `/track`
    (IDEM-01, 2026-09-11) routes through `IdempotencyStore` (atomic
    SETNX + atomic Lua mutate) so SDK network retries return the
    stored response instead of minting a fresh `reservation_id`.

    Wire codes are wire-shape-strict — renaming a `GateErrorCode`
    variant is a major-bump protocol change because SDK switch
    statements branch on the string. The HTTP status mapping is
    per-code; HTTP 200 + block body is intentional for `/gate` (the
    gate is a pre-flight probe, SDK branches on the body) but
    pre-fix `/execute` defaulted to 200 with block body too — that
    was the silent fail-OPEN class DEF-DESTR-RUNNER-HTTP-STATUS
    closed. The kill signal cannot be silently dropped —
    `WorkflowKilledInterrupt` inherits from `NullRunError` and
    `except Exception:` catches it; an SDK that catches only
    `NullRunBlockedException` and swallows everything else will leak
    the kill. The `on_error` hook fires for every `NullRunError`
    including kill — operators who wire Sentry capture on the hook
    will see kill events; filter on `error_code` (`"NR-W002"`) to
    skip them. The `is_approximate: true` flag on
    `ApproximateBudgetResponse` is mandatory — never render a 0¢
    spend on the 503 path (`BUDGET_DATA_UNAVAILABLE`), only a "data
    unavailable" CTA.
