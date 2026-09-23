title: Control plane (real-time control)
maturity: stable
description: Real-time WebSocket channel for kill, pause, and approval_resolved — the operator's runtime control surface for live agents.
# Control plane (real-time control)

The **control plane** is the live channel between the dashboard and
your running agent. When you click **Pause**, **Resume**, or **Kill**
in the dashboard, the signal reaches your SDK through the WebSocket
push channel. Without the control plane, the dashboard would only
tell the agent something happened on its next `/gate` call. With it,
the agent learns in real time.

## What the dashboard can do

From the workflow detail page (or the top-level **Workflows** list):

| Action | Effect on the agent |
|---|---|
| **Pause** | Every call starts raising `WorkflowPausedException` (a `NullRunError` subclass). Resume to undo. |
| **Resume** | Unpause — calls resume normally. |
| **Kill** | Every call raises `WorkflowKilledInterrupt` (alias `NullRunWorkflowKilledError`). The agent loop dies. |

For the agent, the difference between Pause and Kill:

- **Pause** — recoverable. The agent can catch `WorkflowPausedException`,
  do clean-up, and either retry or wait.
- **Kill** — terminal. The exception inherits from `NullRunError` and
  is caught by `except Exception:` like every other SDK error — handle
  it explicitly if you need to checkpoint state before the process exits.

The agent doesn't have to wait for the next `@protect` call to learn.
If it's mid-LLM-call when you click Kill, the SDK raises the
exception at the next yield boundary inside the agent's loop.

## How the signal reaches your SDK

The dashboard pushes signals over a WebSocket connection that the SDK
opens automatically on the first `@protect` call. The connection is
authenticated with the same API key the SDK uses for `/gate` and
`/track`, plus HMAC signature verification.

The SDK keeps the connection alive with background heartbeats. If
the WebSocket disconnects (network blip, firewall, gateway restart),
the SDK falls back to polling `GET /api/v1/status/:workflow_id` once
per second until the WebSocket comes back. From the agent's
perspective, the control plane still applies — kill/pause still
arrive on the next gate or yield boundary.

The control-plane transport is auto-negotiated by the SDK — WS push
in production traffic with HTTP-polling fallback when the WS
connection drops repeatedly. You don't need to opt in or pass any
flag; the SDK handles both transports internally. For most agents
this is invisible: the first `@protect` call opens the WS, and the
gateway's Pause / Kill / `approval_resolved` signals arrive in
real time without any further setup.

## What your agent sees {#how-the-sdk-reacts}

The two exceptions your agent code will encounter:

```python
from nullrun import WorkflowKilledInterrupt

@nullrun.protect
def my_agent_step(prompt):
    # ... agent logic ...
    return result

try:
    my_agent_step("do something")
except NullRunWorkflowKilledError:
    # Operator killed the workflow. Re-raise, or checkpoint then re-raise.
    raise
except WorkflowPausedException:
    # Operator paused the workflow. Wait or exit cleanly.
    raise
```

Both signals inherit from `NullRunError`, so `with nullrun.handle():`
catches both (prints the structured four-line developer report, exits
1). To handle kill distinctly — checkpoint state, notify a
supervisor, then exit — wrap the un-`handle()` call in your own
try/except. See
[Error handling → Kill signal](../concepts/error-handling.md#kill-signal)
for the recommended handler shape.

For Pause, you have more flexibility. Most production agents catch
`WorkflowPausedException`, save their state to durable storage,
wait a few seconds, and resume. Some simply exit and let a
supervisor process restart them when the workflow is unpaused.

## Approval events

The same WebSocket push channel carries the second event type the SDK
needs: **`approval_resolved`**. When the gate returns
`decision = require_approval` on a `/gate` call, the parked SDK
agent's thread waits on a `threading.Event` until the operator
clicks Approve or Deny on the dashboard. The `approval_resolved` WS
push wakes the event; the SDK resumes the agent with the operator's
outcome.

The complete approval flow is documented in
[Human approval → Approval resume flow](human-approval.md#approval-resume-flow).
If the approval timeout expires, the SDK raises
`WorkflowKilledInterrupt`. There is no silent approval — operators
must decide explicitly.

## What if the SDK is disconnected?

If the WebSocket is down and polling is also blocked, the SDK can't
learn about a kill until the next `/gate` call. In practice this
window is at most one LLM-call duration — typically seconds, never
minutes.

The dashboard records the kill timestamp. When the SDK reconnects,
it queries the workflow's state and acts on the most recent kill —
even if the kill happened during the disconnection. The agent picks
up the kill on the next call, with the original timestamp preserved
in the audit log.

## Common operations

### Pause a runaway agent

1. Open **Workflows** in the sidebar.
2. Find the row whose status is **Active** but whose spend is
   suspiciously climbing.
3. Click the row, then click **Pause**.
4. The dashboard shows "Pause sent" with the timestamp.
5. Within ~1 second, the agent stops calling LLM.

### Resume after a pause

1. Same workflow page.
2. Click **Resume**.
3. The agent's next call succeeds.

### Kill an agent that won't stop

1. **Workflows** → workflow row → **Kill**.
2. The agent receives `WorkflowKilledInterrupt` (or its typed alias
   `NullRunWorkflowKilledError`) on the next yield point inside its
   loop. See [Error handling](../concepts/error-handling.md#kill-signal).
3. The signal inherits from `NullRunError`, so a bare `except Exception:`
   arm catches it. If you want a clean shutdown on kill, catch the
   typed exception **explicitly** and re-raise it — the kill contract
   is "operator's word is final".

### Verify the signal arrived

After clicking Pause / Kill, the workflow's status flips
immediately in the dashboard. If the agent doesn't respond, check
the SDK logs — the WebSocket connection state is logged at startup
and on every reconnect.

## See also

- [Workflows → how to control one](workflow.md#how-to-control-one)
- [Human approval](human-approval.md) — similar flow for tool
  approvals
- [Troubleshooting](../troubleshooting.md) — "why did my workflow
  pause without me doing anything?"

!!! info "Deep dive"

    The control plane is a WebSocket at
    `GET /ws/control/:organization_id`
    (`backend/src/proxy/http/ws_control.rs`, `ws_control_handler`).
    Auth is the same `X-API-Key` / `Authorization: Bearer` used on
    `/gate` / `/track`; SEC-7 explicitly rejects API keys in query
    strings because query params are routinely captured by
    reverse-proxy access logs and HTTP referer headers. The upgrade
    calls `ws.on_upgrade` and lands in `ws_control_socket`; the
    socket subscribes to `EventBus` for the organization's channel
    and converts every `WorkflowEventEnvelope` via
    `convert_envelope_to_ws_message`. State changes are emitted as
    `WsMessage::StateChange { state: WsWorkflowState, message_id:
    Option<String> }` — `Paused` and `Killed` carry a `message_id`
    so the SDK can ACK them. Approvals surface as
    `WsMessage::ApprovalResolved { outcome: WsApprovalOutcome, note,
    decided_by, organization_id, ... }`. Frames are HMAC-signed
    per-org via `SignedWsMessage::new` using the canonical-serialize
    (RFC 8785 JCS subset) bytes for the signing input. The
    HTTP-poll fallback lives at
    `GET /api/v1/status/:workflow_id`
    (`backend/src/proxy/handlers.rs`, `status_handler`) — it
    emits `state` as PascalCase (`State::as_pascal_case`) so the
    SDK's `check_control_plane` matches without casing drift.

    State transitions are validated at the source via
    `State::validate_transition` (`backend/src/decision/mod.rs`):
    `Killed → *` is terminal — no transitions out, ever. The WS
    frame carries a `version` field per `EventMetadata.sequence`
    (`event_bus.rs`) so a re-syncing SDK can detect missed events;
    the SDK calls `WsMessage::ResyncRequired` to ask for a full
    re-fetch. Cross-org envelope leakage is blocked at the
    converter (`ws_control.rs`, NR-094): the `expected_org_id`
    parameter must match the payload's `organization_id` for the
    four variants that carry it (`StateChanged` /
    `PolicyInvalidated` / `KeyRotated` / `ApprovalResolved`); a
    mismatch drops the event with a `tracing::warn!` and never
    reaches the wire. WS frames are HMAC-signed with a 5-minute
    max-age window (`WS_HMAC_MAX_AGE_SECONDS = 300`); pre-auth
    error frames and keepalive pongs are intentionally unsigned.
    The status-poll endpoint re-emits state on every call so a
    disconnected SDK picks up the most recent kill on reconnect,
    with the original timestamp preserved in the audit log via
    `record_audit_event_simple` on the kill handler.

    The push flow on a kill: `kill_workflow_handler` →
    `service.kill_workflow` (DB lifecycle UPDATE) →
    `record_audit_event_simple("workflow.killed")` (P0-19 audit
    breadcrumb, `workflows.rs`) →
    `EventBus::publish(StateChanged { new_state: "killed" })` →
    `ws_control_socket` subscriber →
    `convert_envelope_to_ws_message` →
    `WsMessage::StateChange { state: WsWorkflowState::Killed,
    message_id }` → SDK raises `WorkflowKilledInterrupt` on the
    next yield. The same path applies to pause / resume, with
    `WsWorkflowState::Paused` / `WsWorkflowState::Normal`
    respectively. Approval resolution takes a parallel path:
    `approve_handler` → `publish_approval_resolved` → in-process
    broadcast + Redis pub/sub on `event_bus:approval_resolved`
    (ADR-023 P0-3) → `WsMessage::ApprovalResolved { outcome:
    "approved" }` → SDK's `_wait_for_approval_resolution`
    `threading.Event` wakes up. The SDK's transport
    auto-negotiates between WS push and HTTP polling; on a
    persistent disconnect the SDK falls back to polling once per
    second until the WS comes back.

    WS push was the chosen path over pure polling because polling
    once per second per agent per workflow is unscalable — at 1000
    active agents × 5 workflows each, that's 5000 status requests
    per second per replica. WS push moves the latency from "next
    polling tick" to "frame delivered" (sub-100ms in production).
    The HTTP-poll fallback is the chosen transport degradation
    strategy over "fail CLOSED on WS disconnect" because a
    transient network blip shouldn't leave the operator unable to
    kill an agent. The `message_id` ACK pattern was chosen over
    fire-and-forget because the gate's StateChange events trigger
    SDK exception raises — losing a kill frame would silently fail
    to kill an agent. Cross-org envelope validation at the
    converter (`expected_org_id` check) was added in NR-094 after
    the pre-fix converter forwarded cross-org payloads because the
    in-process channel narrowing wasn't a sufficient
    defense-in-depth. The PascalCase wire encoding
    (`State::as_pascal_case`) was chosen over reusing the DB
    UPPERCASE form because the SDK's `check_control_plane`
    comparison expects PascalCase; using DB form would have
    silently broken the HTTP-poll fallback.

    The HTTP-poll fallback is bounded by the gate's `wf_active`
    cache TTL (60s) — a paused workflow observed only via polling
    sees the new state at most one minute late. The WS reconnect
    window after a persistent disconnect depends on the SDK's
    auto-negotiation (`run_in_background` reconnect task); if both
    WS and polling are blocked, the SDK learns about the kill on
    the next `/gate` call only — kill latency in the worst case
    is one LLM-call duration. The WS HMAC `max_age_seconds = 300`
    is shared with the HTTP HMAC config
    (`hmac_config.max_age_seconds`); a clock-skew >5min between
    SDK and backend will reject otherwise-valid frames. Legacy
    keys created before HMAC was rolled out carry
    `secret_key = None`; for those the server sends raw
    `WsMessage` (`send_signed_or_raw` fallback) and increments
    `ws_unsigned_messages_total` so the on-call sees the rotation
    signal. The `WsMessage::ApprovalResolved` push is opt-in via
    `?wait_for_approval=true` on the upgrade; without that flag
    the SDK falls back to legacy poll-based resume (deprecated,
    removed in a future release per `ws_control.rs`). Cross-
    replica fan-out for approval events is best-effort Redis
    pub/sub — a publish failure logs and is recovered by the next
    `/approval-state/reconcile` (P1-4) tick. The `Killed` terminal
    state means a re-killed workflow must be re-created as a new
    workflow — there is no reactivation path.
