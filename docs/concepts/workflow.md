title: Workflows
maturity: stable
description: Group agent calls into a named workflow, propagate parent_trace_id, and bind cost to a logical unit instead of a single session.
# Workflows

A **workflow** is one agent you run. In the dashboard it shows up
under **Workflows** in the left sidebar. Each workflow has its own
budget and its own list of API keys.

## What you see in the dashboard

The **Workflows** page lists every workflow you've created. Each
row shows:

- The workflow's name (you picked this when you created it)
- Whether it's **Active**, **Paused**, or **Killed**
- Total spend for the current billing period
- How many API keys are bound to it
- When it last saw traffic

Click a workflow to open its detail page. The detail page has six
tabs:

| Tab | What it shows |
|---|---|
| **Overview** | Name, status (Active / Paused / Killed), current spend vs. the installed budget cap, applied policies, and the **Pause** / **Resume** / **Kill** / **Delete** controls. This is where you change the budget cap. |
| **Policies** | The policies scoped to this workflow. Rate limit, budget limit, and tool block entries — same primitives as the org-level Policies page, filtered to this workflow. |
| **Executions** | Every gate call your agent made — allowed, blocked, rate-limited. The raw list the gate uses to decide what your agent can do. |
| **Traces** | Hierarchical view of one agent run — each LLM call, each tool call, with timing and cost. |
| **API keys** | The API keys bound to this workflow. Use **Generate API key** in the top-right to mint one; the raw key value is shown only once at creation. |
| **Coverage** | MCP servers and tools observed on this workflow in the last 30 days, with the "discovered but not registered" panel for un-enrolled servers. |

## How to create one

1. In the dashboard sidebar, click **Workflows**.
2. Click **New workflow** in the top right.
3. Give it a name (e.g. `"production-support-bot"`). The name shows
   up everywhere — keep it short. Names are 1–255 characters:
   letters, digits, space, and `_ . , - & ( )` are allowed.
4. Optionally set an **External ID** — alphanumeric with `-` and
   `_`, up to 64 characters — for integrations that need to look up
   the workflow from your own systems (e.g. a GitHub repo name or a
   customer account id).
5. Click **Create**. The budget cap is configured on the
   **Overview** tab after creation via a budget-limit policy or the
   installed budget control — there is no starting budget on the
   dialog itself.

<figure class="nr-shot">
  <img class="nr-shot__light" src="../../assets/images/screenshots/workflows-list-light.png"
       alt="Workflows list with the New workflow button highlighted in the top right.">
  <img class="nr-shot__dark" src="../../assets/images/screenshots/workflows-list-dark.png"
       alt="Workflows list with the New workflow button highlighted in the top right.">
  <figcaption class="nr-shot__caption">Workflows · New workflow</figcaption>
</figure>

<figure class="nr-shot">
  <img class="nr-shot__light" src="../../assets/images/screenshots/workflow-new-light.png"
       alt="Create workflow dialog open — Workflow name field and External ID optional field.">
  <img class="nr-shot__dark" src="../../assets/images/screenshots/workflow-new-dark.png"
       alt="Create workflow dialog open — Workflow name field and External ID optional field.">
  <figcaption class="nr-shot__caption">Workflows · Create dialog</figcaption>
</figure>

<figure class="nr-shot">
  <img class="nr-shot__light" src="../../assets/images/screenshots/workflow-detail-light.png"
       alt="Workflow detail page — Overview tab with budget card, applied policies, Pause and Kill controls.">
  <img class="nr-shot__dark" src="../../assets/images/screenshots/workflow-detail-dark.png"
       alt="Workflow detail page — Overview tab with budget card, applied policies, Pause and Kill controls.">
  <figcaption class="nr-shot__caption">Workflows · Workflow detail</figcaption>
</figure>

You'll land on the new workflow's detail page. From there:

- **Mint an API key** under the **API keys** tab. The key value
  (`nr_live_...`) is shown **once** — copy it into your secret
  manager immediately.
- **Point your SDK at it**: export `NULLRUN_API_KEY` and the workflow
  binding happens server-side.

## How to control one

Each workflow has three states that you control from the dashboard
or via the API: **Active**, **Paused**, and **Killed**. Both Pause
and Kill reach your running SDK over a WebSocket push; the agent
doesn't have to wait for the next call to learn. See
[Control plane](control-plane.md) for the full contract, the
exceptions each state raises, and how the signal travels over the
WebSocket.

## The workflow's settings

Five things you control per workflow:

- **Budget** — the per-period cap in cents. Set this first. The
  dashboard shows a horizontal bar of how much you've spent vs. the
  cap.
- **Enforcement mode** — `Hard` (block on budget exceeded) or
  `Soft` (allow over-budget up to an overdraft cap, when there's an
  active chain). Full configuration in
  [Policies → BudgetLimit extra fields](policies.md#budgetlimit-extra-fields).
- **Human approvals** — turn on to require operator approval for
  dangerous tools (payments, deletes, external API mutations).
  Available on Growth+ plans.
- **Tool block list** — the patterns the agent must not call. See
  [Tool policies](tool-policies.md).
- **Trace retention** — how long to keep detailed per-call traces
  (default 30 days, plan-gated up to 90).

## Chain context

A **chain** is a logical grouping across multiple `@protect` calls
inside one user request, declared via `with chain(...)`. Chains are
auto-registered on the first `/gate` call: the chain transitions
from `null → ACTIVE` atomically.

### When chains end

A chain dies on the **first** of:

- `op="end"` is reached in the context manager
- 5 minutes of `/gate` inactivity (idle TTL)
- `max_chain_duration_seconds` exceeded (default 3600)

For long streams, send a `POST /heartbeat` every 30 seconds — see
[Heartbeat → how-to](../how-to/streaming.md#chain-heartbeat).

### Why chains exist

Chains exist primarily to enable **soft-mode budget gating**: with
an active chain, the gate allows the agent to run past its budget
up to an overdraft cap (`max_overdraft_cents` or
`max_overdraft_percent`, whichever is lower). Full soft-mode
contract in
[Policies → BudgetLimit extra fields](policies.md#budgetlimit-extra-fields).

## How the workflow ends

A workflow doesn't have an explicit "end" state in the sense of a
final commit. Instead:

- The workflow stays **Active** across many agent runs. Each run is
  a sequence of `@protect` calls.
- A run is **logically ended** when the agent's loop returns or
  throws.
- A workflow is **paused** or **killed** when you decide, or when
  plan limits (max workflows per plan) cause auto-pause.

There is no "clean up the workflow when done" step. Active workflows
keep their policy, budget, and key bindings. Re-run the agent next
week and the same workflow handles it.

## See also

- [Budgets](budgets.md) — the budget cap and how rollover works
- [Policies](policies.md) — what rules attach to a workflow
- [Control plane](control-plane.md) — how Kill / Pause reach your agent
- [API keys](api-keys.md) — how to mint a key bound to this workflow

!!! info "Deep dive"

    A workflow is a row in `workflows` plus a runtime `State` entry
    in the per-execution in-memory map at
    `backend/src/decision/mod.rs` (`pause`, `kill`, `resume`). When
    the operator clicks **Pause** / **Resume** / **Kill**,
    `pause_workflow_handler` / `resume_workflow_handler` /
    `kill_workflow_handler` in `backend/src/proxy/http/workflows.rs`
    mutate the runtime CB state, write the audit row via
    `record_audit_event_simple`, then push the transition through
    `EventBus::publish_with_origin` (canonical
    `WorkflowEventPayload::StateChanged`,
    `backend/src/proxy/http/event_bus.rs`). The WebSocket upgrade
    handler at `backend/src/proxy/http/ws_control.rs` is subscribed
    to that channel via `subscribe_for_ws`; the envelope is
    converted by `convert_envelope_to_ws_message`
    (`ws_control.rs`) and emitted as
    `WsMessage::StateChange { state: WsWorkflowState }`. Chains are
    stored in Redis as `chain:{org}:{chain_id}` and extended on
    every `/check` with `idle_ttl = 300s`
    (`backend/src/redis/chain.rs`, `backend/src/redis/mod.rs`); the
    default `max_chain_duration_seconds = 3600` lives in
    `backend/src/enforcement/unified_evaluator.rs`.

    State transitions are validated through
    `State::validate_transition` (`backend/src/decision/mod.rs`),
    which makes `Killed → *` terminal — there is no path out.
    `Killed` / `Paused` runtime events write `state = "KILLED"` /
    `"PAUSED"` to the LIFECYCLE-only `workflows.state` column;
    `Flagged` / `Tripped` CB events are gated on
    `map_state_to_lifecycle_column` (None) and instead write
    `cb_state` via `map_state_to_cb_state` (ADR-027 partition fix),
    so the two column-truths never collide on the
    `chk_workflows_state` CHECK constraint. The state field emitted
    on the WS wire is PascalCase (`State::as_pascal_case`,
    `decision/mod.rs`) so the SDK's `check_control_plane` comparison
    matches; the HTTP-poll fallback `status_handler`
    (`backend/src/proxy/handlers.rs`) emits the same PascalCase.
    WebSocket frames are HMAC-signed with the per-org `secret_key`
    (`SignedWsMessage::new`, `ws_control.rs`) and the WS upgrade
    rejects API keys in query strings (SEC-7, `ws_control.rs`).
    Cross-org envelope leakage is blocked by the `expected_org_id`
    check in `convert_envelope_to_ws_message` (`ws_control.rs`,
    NR-094). Chains are fail-safe via TTL only — Redis EXPIRE on
    the chain key is the sole cleanup mechanism, with no worker
    reaping stale rows.

    Workflow lifecycle writes are split across three concerns: the
    CB runtime (in-memory + Redis), the DB lifecycle row
    (`update_workflow_state` with `chk_workflows_state`-safe
    mapping), and the EventBus broadcast. Each handler emits a
    `tracing::warn!` plus a `record_audit_event_simple` row carrying
    `actor_type` / `actor_id` (kill: P0-19, pause: DEF-TS12GRT-001 —
    see `workflows.rs`), so a manual kill surfaces in both
    `docker logs` and `/control-center/audit-log`. The same
    EventBus payload drives three downstream consumers: WS
    subscribers, alert dispatch
    (`crate::alert::dispatch_workflow_state_alert`), and the
    policy-cache invalidation. Chain context is a separate, opt-in
    construct — `with chain(...)` only matters when soft-mode budget
    is on, and the chain dies on first of `op="end"` / 5-minute
    idle TTL / max-duration TTL.

    The v3.56 split (ADR-011) moved the orchestrator's 10 priority
    steps into `backend/src/proxy/http/gate/orchestrator.rs`,
    collapsing the prior 8934-line `gate_internal` into a 3-arm
    dispatcher via `gate_wire_adapter`. The chosen path keeps the
    wire contract identical
    (`GateResponse::{allow, block, require_approval}` are preserved
    verbatim) but unifies the internal `EvaluationDecision` enum
    across gate / preview / shadow consumers — closing the 38-arm
    mismatch where simulation could emit `FALLBACK` while production
    gate emitted `REQUIRE_APPROVAL`. State separation between
    `workflows.state` (lifecycle) and `workflows.cb_state` (CB
    runtime, ADR-027) was the
    alternative-considered-and-rejected pattern of "single state
    column" — that column would have tripped CHECK constraints on
    every CB trip.

    The 5-minute chain idle TTL (`CHAIN_IDLE = 300`,
    `redis/mod.rs`) is hard-coded; there is no per-organization
    override, so long-running agents must call `POST /heartbeat`
    every 30 seconds (`docs/adr/INDEX.md`, streaming ADR) or the
    chain dies mid-run. The HTTP-poll fallback window is bounded by
    the gate's `wf_active` cache TTL (60s) — a paused workflow
    observed only via HTTP polling sees the new state at most one
    minute late. WebSocket reconnect after a network blip is
    auto-negotiated, but if both WS and polling are blocked the SDK
    learns about the kill on the next `/gate` call only — kill
    latency in the worst case is therefore one LLM-call duration.
    `Killed` is terminal with no documented reactivation path; a
    "re-killed" workflow must be re-created as a new workflow.
