# Control plane (real-time control)

The **control plane** is the live channel between the dashboard and
your running agent. When you click **Pause**, **Resume**, or **Kill**
in the dashboard, the signal reaches your SDK within a second — even
if the agent is in the middle of an LLM call.

Without the control plane, the dashboard would only tell the agent
something happened on its next call. With it, the agent learns in
real time.

## What the dashboard can do

From the workflow detail page (or the top-level **Workflows** list):

| Action | Effect on the agent |
|---|---|
| **Pause** | Every call starts raising `WorkflowPausedException` (an `Exception`). Resume to undo. |
| **Resume** | Unpause — calls resume normally. |
| **Kill** | Every call raises `WorkflowKilledInterrupt` (a `BaseException`). The agent loop dies. |

For the agent, the difference between Pause and Kill:

- **Pause** — recoverable. The exception is a regular `Exception`,
  the agent can catch it, do clean-up, and either retry or wait.
- **Kill** — terminal. The exception is a `BaseException`, the
  agent cannot catch it in `except Exception:` blocks (which is the
  point — you don't want a runaway loop swallowing the kill).

The agent doesn't have to wait for the next `@protect` call to learn.
If it's mid-LLM-call when you click Kill, the SDK raises the
exception at the next yield boundary inside the agent's loop.

## How the signal reaches your SDK

The dashboard pushes signals over a WebSocket connection that the SDK
opens automatically when `init()` runs. The connection is
authenticated with the same API key the SDK uses for `/gate` and
`/track`, plus HMAC signature verification.

The SDK keeps the connection alive with background heartbeats. If
the WebSocket disconnects (network blip, firewall, gateway restart),
the SDK falls back to polling `GET /workflows/{id}` once per second
until the WebSocket comes back. From the agent's perspective, there's
no difference — kill/pause still arrive within ~1 second.

In environments where the WebSocket is firewalled, you can force the
SDK into polling mode by constructing the runtime directly:

```python
from nullrun.runtime import NullRunRuntime

runtime = NullRunRuntime(api_key="...", polling=True)
```

This is internal-only — `polling=True` is not exposed as an env var
because it's a deploy-time decision, not something you want to flip
per-request.

## What your agent sees

The two exceptions your agent code will encounter:

```python
from nullrun.breaker.exceptions import WorkflowKilledInterrupt

@nullrun.protect
def my_agent_step(prompt):
    # ... agent logic ...
    return result

try:
    my_agent_step("do something")
except WorkflowKilledInterrupt:
    # Operator killed the workflow. This is BaseException — propagate it.
    raise
except WorkflowPausedException:
    # Operator paused the workflow. Wait or exit cleanly.
    raise
```

In practice, if you use the zero-boilerplate `@guarded` decorator,
you don't need to write this — `WorkflowKilledInterrupt` propagates
through `@guarded` because `@guarded` only catches `NullRunError`
subclasses, and the kill signal is `BaseException`.

For Pause, you have more flexibility. Most production agents catch
`WorkflowPausedException`, save their state to durable storage,
wait a few seconds, and resume. Some simply exit and let a
supervisor process restart them when the workflow is unpaused.

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
2. The agent receives `WorkflowKilledInterrupt` on the next yield
   point inside its loop.
3. If the agent's loop catches `Exception` (but not `BaseException`),
   the kill propagates through. If the agent catches `BaseException`
   explicitly, make sure it re-raises `WorkflowKilledInterrupt` —
   the kill contract is "operator's word is final".

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
