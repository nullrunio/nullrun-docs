---
title: Control plane
maturity: stable
description: The live channel between the control center and a running agent — pause, resume, and kill, delivered over a WebSocket with an HTTP fallback.
---

# Control plane (real-time control)

The **control plane** is the live channel between the control center and a
running agent. An operator clicks **Pause**, **Resume**, or **Kill**,
and the agent reacts while it runs.

## What the operator can do

| Action | What the agent does |
|---|---|
| **Pause** | Protected calls are refused with `WorkflowPausedException` (`NR-W003`). The agent can catch it, save state, and wait. |
| **Resume** | Protected calls run normally again. |
| **Kill** | Protected calls are refused with the kill signal (`NR-W002`). See [Sync and async behave differently](#sync-and-async-behave-differently). |

Kill is terminal. A killed workflow does not run again.

Pause is recoverable. The agent can catch the exception, checkpoint,
and try again.

## How the signal reaches the SDK

The SDK opens a WebSocket to
`wss://api.nullrun.io/ws/control/{organization_id}` on its first
protected call. The upgrade request carries the same API key the SDK
uses for every other request, in the `X-API-Key` and `Authorization`
headers. It carries no body, so it carries no request signature. The
server signs every frame it sends. When the SDK holds the signing
secret, it verifies the signature before it reads anything out of the
frame, and refuses a frame that arrives unsigned. A key without a
secret cannot verify, and the frame is read as it arrives.

The SDK keeps a copy of the control-plane state for each workflow it
tracks:

- With the WebSocket connected, the server pushes every state change.
- Without a pushed state, the SDK reads the workflow state over HTTP
  from `GET /api/v1/status/{workflow_id}`.

Set `NULLRUN_TRANSPORT=http` to run the HTTP poll instead of the
WebSocket. The poll runs once per second and suits environments where
the WebSocket endpoint is blocked.

The SDK chooses the transport for you. You do not pass a flag to
enable the control plane.

## What the agent sees

Two exceptions cover the whole control plane:

| Exception | Code | Meaning |
|---|---|---|
| `WorkflowPausedException` | `NR-W003` | The operator paused the workflow. |
| `WorkflowKilledInterrupt` | `NR-W002` | The operator killed the workflow. `NullRunWorkflowKilledError` is a typed subclass with the same code. |

`WorkflowPausedException` carries `resume_after`: the number of
seconds the pause lasts. It is `None` when the pause carries no
duration.

### Sync and async behave differently

The decorator translates the signal differently in a synchronous
function and in a coroutine.

| Protected function | What propagates |
|---|---|
| Sync | The signal is re-wrapped as `NullRunBlockedException` with `error_code` `NR-W002` or `NR-W003`. The `on_error` hook fires. |
| Async | The raw `WorkflowKilledInterrupt` or `WorkflowPausedException` propagates. The `on_error` hook does not fire. |

An async framework cancels a task on the original exception type, so
the async wrapper leaves it alone.

```python
import nullrun
from nullrun import WorkflowKilledInterrupt, WorkflowPausedException

nullrun.init(api_key="nr_live_...")


@nullrun.protect
def my_agent_step(prompt):
    # ... agent logic ...
    return result


try:
    my_agent_step("do something")
except WorkflowKilledInterrupt:
    # The operator killed the workflow. Checkpoint, then re-raise.
    raise
except WorkflowPausedException:
    # The operator paused the workflow. Save state and wait.
    raise
```

`nullrun.guard()` handles the pause: it prints the developer report
and exits with status 1. The kill follows the same split as the
decorator. On the async path `guard()` re-raises it, so the kill
reaches the top of the agent loop. On the sync path the kill is
already a `NullRunBlockedException`, so `guard()` prints the report
and exits with status 1.

## Approval events

The same WebSocket carries approval decisions. When the gate returns
`require_approval`, the parked agent waits for the operator. The
decision arrives over the control plane and the agent resumes with the
outcome.

If the approval window expires, the SDK raises
`NullRunApprovalExpiredError` (`NR-A012`). An approval never resolves
silently.

The full approval flow is in
[Human approval](human-approval.md#approval-resume-flow).

## Operator steps

### Pause a runaway agent

1. Open **Workflows** in the sidebar.
2. Open the workflow row.
3. Click **Pause**.
4. The workflow status changes, and the agent stops at its next protected call.

### Resume a paused agent

1. Open the workflow.
2. Click **Resume**.
3. The next protected call succeeds.

### Kill an agent

1. Open the workflow.
2. Click **Kill**.
3. The agent receives the kill signal at its next protected call.

Catch the kill explicitly and re-raise it. A bare `except Exception:`
arm swallows the signal.

## See also

- [Workflows](workflow.md) — where a workflow runs
- [Human approval](human-approval.md) — the approval round trip
- [Error handling](error-handling.md) — the exception each refusal raises
