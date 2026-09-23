title: Circuit breaker
maturity: stable
description: How NullRun's circuit breaker trips on a budget overrun, recovers after a cooldown, and propagates a kill signal across in-flight calls.
# Circuit breaker

The circuit breaker stops your agent when something goes wrong. When
the agent is hitting the budget cap, calling a tool your policies
forbid, or being asked by an operator to stop — the gate returns
`block` and the SDK raises an exception, even if the agent's code
doesn't know to stop.

The underlying mechanism is a single `/api/v1/gate` evaluation per
`@protect`-wrapped call that returns `allow` / `block` /
`require_approval`.

In the dashboard, a tripped breaker shows up as the workflow's status
flipping from **Active** to **Killed** or as a flood of **block**
decisions in the **Audit log**.

## When does it trip?

The gate reacts to three categories of situation. Each is a separate
decision path inside `/gate`, but to you it all looks the same: the
next call rejects.

| Situation | What you see | Where in the dashboard |
|---|---|---|
| **Budget exceeded** (Hard mode) | Every call returns `block`; SDK raises `NullRunBudgetError` with `error_code = "NR-B004"` | Audit log, then the spend bar hits 100% |
| **Tool blocked** by policy | `block`; SDK raises `NullRunToolBlockedError` with `error_code = "NR-T001"` | Audit log |
| **Operator kill** | `WorkflowKilledInterrupt` (alias `NullRunWorkflowKilledError`) raised mid-call | Workflow status flips to **Killed** |

Rate limiting (429) and budget soft-mode blocks are returned by the
same gate but with different codes. SDK surfaces them as `error_code = "NR-R001"` and `error_code = "NR-B004"`. See [Budgets](budgets.md#soft-mode) and [Policies](policies.md).

The first two are automatic — the gate enforces them on every call.
The third needs you to click **Kill** in the dashboard or call
`POST /api/v1/workflows/{id}/kill`.

## What the agent sees

When the breaker trips, the SDK raises an exception. The exact
exception depends on what tripped it:

| Trip cause | Exception | Class |
|---|---|---|
| Budget exceeded | `NullRunBudgetError` (`error_code = "NR-B004"`) | `NullRunError` (Exception) |
| Tool blocked | `NullRunBlockedException` (`error_code = "NR-T001"`) | `NullRunError` (Exception) |
| Operator kill | `WorkflowKilledInterrupt` (alias `NullRunWorkflowKilledError`) | `NullRunError` (Exception) |

The kill signal inherits from `NullRunError`, so `try/except Exception:`
catches it like every other SDK error. To handle kill specifically
— checkpoint state, notify a supervisor, exit cleanly — catch
`NullRunWorkflowKilledError` (preferred) or `WorkflowKilledInterrupt`
explicitly. See [Error handling → Kill signal](../concepts/error-handling.md#kill-signal)
for the recommended handler shape.

If you use the zero-boilerplate helpers from the SDK, you don't have
to write any of this — `with nullrun.handle():` catches the standard
exceptions (including the kill signal), prints the structured
four-line developer report, and exits 1. To handle kill distinctly,
use the un-`@guarded` `protect()` form.

## When the gateway is unreachable

Sometimes the gateway itself is down — DNS, network, an outage.
The mental model: critical paths (budget reservation, ToolBlock,
aggregate rate limit) refuse to run when the gateway can't be reached;
secondary signals (per-key rate limit) may let calls through. When the
gateway rejects because of an infrastructure failure, you'll see a
clear HTTP error from the SDK.

If you're seeing persistent infrastructure failures, contact support.

## When the breaker recovers

After the gateway comes back, the gate transitions automatically to
normal mode. No operator action needed — the next `/gate` call
succeeds if the policy allows it.

If the gate is blocking too often (every call rejects), look at:

1. The **Audit log** for the workflow. The reason column tells you
   why each call was blocked.
2. The workflow's **Overview** tab — the spend vs. cap bar shows
   whether you're consistently hitting the budget. Raise the cap or
   switch to a cheaper model if so.
3. **Effective policy** (on the **Policies** tab). A policy you added
   recently may be too strict — try narrowing patterns or scoping to
   one workflow before rolling out org-wide.

## Common scenarios

### "My agent suddenly stopped responding"

Open the workflow in the dashboard. Check the state:

| Status | What happened |
|---|---|
| **Active** | The agent is fine — check the application logs for the actual error |
| **Paused** | You paused it (or an operator did). Click **Resume** to restart. See [Control plane](control-plane.md). |
| **Killed** | You killed it (or an operator did). Create a new workflow or re-activate. |

If the status is Active but every call rejects, open the
**Audit log** and filter by `decision = block`. The reason column
shows the pattern that matched.

### "My agent was working yesterday and is blocked today"

Look at the workflow's **Overview** tab — the spend bar. The budget
probably rolled over (new month or billing cycle renewal) and the new
period started with an empty counter. Raise the cap or wait for the
next reset.

### "I want to test my agent without the breaker tripping"

Use a **separate workflow** with its own (low or zero) budget. Don't
disable the gate — bypassing it is a dev/test opt-out.

## See also

- [Budgets](budgets.md) — the most common trip cause
- [Tool policies](tool-policies.md) — your own blocking rules
- [Human approval](human-approval.md) — the alternative to blocking
  for sensitive operations you actually want to allow
- [Troubleshooting](../troubleshooting.md) — common "why is my
  agent blocked?" questions

## Deep dive

!!! info "Deep dive"

    The circuit breaker is the `/api/v1/gate` enforcement pipeline in
    `backend/src/proxy/http/gate/`, with three independent paths that
    can trip it. **Budget exceeded** is enforced atomically by
    `reserve_v3.lua` (`backend/src/redis/scripts/reserve_v3.lua`) —
    Lua §6a runs an always-strict org ceiling, §6 runs the workflow
    ceiling, then the period-bound counter check, all in one `EVAL`;
    on overflow the binding status flips to `blocked` (ADR-016 §2.6)
    and the gate returns a 5-tuple diagnostic `{spent, budget,
    projected}` to the orchestrator. **Tool block** is enforced by
    `check_tool_block` in `backend/src/proxy/http/gate/orchestrator.rs`
    — it resolves the canonical tool list from `req.tools ++ req.tool`
    (TB-1/TB-4 fail-CLOSED fixes), looks up the per-key
    `KeyPolicy.tool_patterns`, and runs `glob_match` against every
    pattern. **Operator kill** flows through
    `kill_workflow_handler` (`backend/src/proxy/handlers.rs`) →
    `CircuitBreaker::kill_legacy` (`backend/src/decision/mod.rs`),
    which validates the `State::Killed` transition per ADR-007,
    flips state, and publishes a
    `WorkflowEventPayload::StateChanged { new_state: "killed" }` to
    the EventBus; `ws_control.rs` consumes that envelope and pushes
    `WsMessage::StateChange` with `WsWorkflowState::Killed` over the
    per-org WebSocket so the SDK raises `WorkflowKilledInterrupt`.
    ADR-055 (shipped 2026-09-21) wired `RedisCircuitBreaker` and
    `PostgresCircuitBreaker` into 9 Redis + 19 Postgres hot-path
    sites, so a Redis or Postgres partition now short-circuits
    sub-100ms instead of hanging 5–10s on `pool.acquire()`.

    Every rejection on the budget and ToolBlock paths is fail-CLOSED.
    `reserve_v3.lua` rejects `EXECUTION_NOT_BOUND` /
    `EXECUTION_ORG_MISMATCH` / `EXECUTION_KEY_MISMATCH` before
    touching any counter, and `check_tool_block`'s TB-1 / TB-4
    branches reject when `tools` is absent while `tool_patterns` is
    non-empty or when the policy cache is unavailable. Per-org
    aggregate rate limit is FailClosed (Hard); the per-key default is
    FailOpen with the budget gate as the authoritative backstop
    (ADR-029 §2). `/gate` is idempotent on retry via `IdempotencyStore`
    at `gate.rs` (atomic SETNX + atomic Lua mutate) so network retries
    return the stored response instead of minting a fresh
    `reservation_id` (IDEM-01, 2026-09-11). `execution_id` is
    server-minted (UUIDv7 at
    `backend/src/proxy/http/gate/execution_id.rs`) and bound to
    `(org_id, api_key_id)` in `execution:{id}` — the binding is the
    single source of truth for the reserve/consume pair (ADR-003),
    and the kill signal inherits from `NullRunError` so
    `except Exception:` catches it alongside every other SDK error.

    Server-minted identity threads through the whole pipeline. The
    canonical tool name matcher at `validate_tool_name` rejects
    control characters on both the singular `tool` field and every
    entry of the plural `tools[]` array (DEF-SDKT-002), and ToolBlock
    patterns use the `glob_match` family: `*` alone matches
    everything, `prefix.*` smart-matches `prefix` AND
    `prefix.anything`, and multi-`*` patterns split on every star and
    require literal segments in order — `*.drop_*` matches
    `s3.drop_table` (v3.39 / DEF-POLFLOW-TB-06). The orchestrator at
    `run_gate_orchestrator` runs in priority order: workflow_active
    → parent_ownership → cycle_depth_check → tool_block →
    business_impact_validate → rate_limit → budget_reserve, with
    the first non-`Allow` decision winning (`Block > RequireApproval
    > Allow` per ADR-011). For multi-wf shared org budgets, ADR-050
    ships a single per-org counter shared by all workflows so
    exhausting the org budget via workflow A naturally blocks
    workflow B (enforced in Lua §6a via `org_budget_cents` from
    `AggregatedPolicy.org_budget_cents`).

    Two design alternatives were considered and rejected: (1)
    **Inline arms in `gate_internal` (pre-v3.56)** — each enforcement
    step was a flat arm in the monolithic `gate_internal` function,
    and the unified orchestrator now composes the same checks via
    lifted helpers but keeps the inline arms until the H.1 dispatcher
    activation lands (wire shape unchanged at runtime); (2)
    **Per-org circuit-breaker state** — rejected because Redis /
    Postgres are global infra and per-org breakers would be premature
    optimization (ADR-055 §"Not changed"). ADR-055 chose to wrap
    existing `pool.acquire()` calls in `RedisCircuitBreaker::execute()`
    and `PostgresCircuitBreaker::execute_with_degraded()` rather than
    rewrite the call sites, which means `read_binding` now takes an
    explicit mode parameter (FailClosed for orchestrator
    parent_ownership, Degraded for `/track` re-read). The 30%
    anti-DoS `RESERVED_CAP_EXCEEDED` check was moved into the
    soft-pass branch (v3.21) because pre-fix soft-mode bypass could
    accumulate unbounded reservations and silently bypass the cap.

    Per-org breaker state is a deliberate non-feature — the
    Postgres breaker is per-binary global, not per-org, which is
    acceptable for infra failure (Postgres down = all orgs affected).
    In-flight partial reservations before circuit trip rely on
    envelope TTL (24h) for cleanup, a documented trade-off
    (ADR-055 PR-C §"Trade-offs"). The breaker is wired into 9 Redis
    + 19 Postgres sites but enforcement sites outside that set
    (workers, outbox processor) rely on the worker pool's natural
    backpressure. The WS push for kill delivery has its own transport
    fallback: if the WebSocket is down, the SDK's heartbeat polling
    picks up the kill — so delivery latency is bounded by the
    heartbeat interval, not zero. `reserve_v3.lua`'s
    `RESERVED_SCANNED_PARTIAL` return fires if the inline SCAN over
    `budget:reserved:{org_id}:*` exceeds 256 iterations (NR-015
    audit) — fail-CLOSED, with the partial-scan rate on the dashboard
    as the cue to scale up.
