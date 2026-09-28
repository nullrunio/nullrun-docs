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

Both signals inherit from `NullRunError`. `with nullrun.guard():`
catches `WorkflowPausedException` (prints the structured four-line
developer report, exits 1) and re-raises `WorkflowKilledInterrupt`
— kill is a control-plane action, not an SDK failure, and must reach
the top of the agent loop. To handle kill distinctly — checkpoint
state, notify a supervisor, then exit — wrap the un-`guard()` call
in your own try/except. See
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

    The control plane is a WebSocket connection authenticated with
    the same credentials the SDK uses for gate and tracking calls.
    API keys are never accepted in the query string, because query
    parameters are routinely captured in access logs and referrer
    headers. The connection subscribes to the organization's event
    channel, and every frame is signed per organization. A frame
    older than the maximum accepted age is rejected, so a receiver
    whose clock drifts by more than that window will drop
    otherwise-valid signals. Frames sent before the handshake
    completes, along with keepalive replies, are unsigned by design.

    Each frame carries a sequence number, which lets a reconnecting
    SDK notice that it missed events and ask for a full resync.
    State-change frames for pause and kill also carry a message
    identifier the SDK can acknowledge, so a lost kill frame is not
    silently lost. Every envelope is checked against the connecting
    organization before it is converted for the wire; an envelope
    naming a different organization is dropped rather than
    delivered.

    State transitions are validated at the source, and the killed
    state is terminal — no transition leads out of it, and a killed
    workflow cannot be reactivated. Kill and pause follow the same
    route: the transition is recorded, the state change is
    published, the push channel carries it, and the SDK raises the
    matching exception at its next yield point. The polling
    fallback re-reports the current state on every call, so a
    reconnecting SDK picks up a kill that happened while it was
    disconnected, with the original timestamp preserved in the audit
    log.

    Push delivery is the fast path, in the sub-100ms range, while
    the fallback polls once per second. A workflow observed only by
    polling can reflect a new state as much as a minute late,
    because the poll reads through a cached workflow-activity
    value. If both transports are blocked, the SDK learns of a kill
    on the next gate call, so the worst case is one LLM-call
    duration. Approval resolution rides the same channel and is
    requested by the SDK when an agent parks on `require_approval`;
    fan-out of that event to other replicas is best-effort, and a
    publish that does not land is recovered by the next
    reconciliation pass.
