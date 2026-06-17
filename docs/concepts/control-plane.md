# Control plane (WebSocket)

The control plane is a real-time channel between the NullRun gateway
and connected SDKs. It carries the events that need to land at the
agent **while it is running** — kill / pause decisions, policy
changes, key rotations, and replay-required resyncs.

Without the control plane, the SDK would only learn about a kill when
the next gate call (`@protect`) does a synchronous `check_control_plane`
poll. With it, the SDK learns in milliseconds and can raise the
appropriate exception mid-call.

## Endpoint

```
WSS /ws/control/{org_id}
```

The handshake is authenticated with an `X-API-Key` + HMAC signature,
identical to the SDK REST endpoints. The SDK opens the connection
automatically once both `NULLRUN_API_KEY` and `NULLRUN_SECRET_KEY`
are set. The control plane URL is **not** a public env var — the
SDK constructs it from the API base URL (`NULLRUN_API_URL`,
default `https://api.nullrun.io`) as `wss://<api-host>/ws/control`.

## Message types

Server → client:

| Type | When |
| --- | --- |
| `InitialState` | First message after subscribe; full per-workflow state snapshot |
| `StateChange` | A workflow was killed, paused, or resumed |
| `PolicyInvalidated` | A policy in your workspace changed; cached decisions must be re-evaluated |
| `KeyRotated` | An API key was rotated; cached auth state must be refreshed |
| `ResyncRequired` | Server asks the client to drop local state and re-fetch |
| `Error` | Protocol error |
| `Pong` | Heartbeat reply |

Client → server:

| Type | When |
| --- | --- |
| `Subscribed` | After receiving `InitialState`, ack the subscription |
| `Ack` | Generic ack for any server message that requires one |

## How the SDK reacts

| Server message | SDK action |
| --- | --- |
| `StateChange` (killed) | Raise `WorkflowKilledInterrupt` on the next gate call. If a call is currently mid-execution, the interrupt is queued and raised at the next yield point. |
| `StateChange` (paused) | Raise `WorkflowPausedException` on the next gate call. |
| `PolicyInvalidated` | Drop cached policy decisions; the next gate call re-evaluates. |
| `KeyRotated` | Refresh cached credentials; the next call uses the new key. |
| `ResyncRequired` | Drop local workflow / policy state and re-fetch from `/api/v1/orgs/{org_id}/status`. |

The kill contract (see `docs/kill-contract.md` in the gateway repo)
defines which events are recoverable vs terminal.

## Operator UI

The dashboard's **Workflows → `<workflow_id>` → Actions** panel sends
`StateChange` messages. `PolicyInvalidated` is sent automatically when
a policy is saved. `KeyRotated` is sent when `DELETE
/api/v1/orgs/{org_id}/api-keys/{key_id}` succeeds.

## When the WebSocket is down

If the connection drops, the SDK falls back to polling: every
`@protect` call invokes `check_control_plane` synchronously against
`/api/v1/orgs/{org_id}/status`. This is slower (a few hundred ms per
gate call) but correct — kills and pauses still land.

To disable the WebSocket path entirely (test / air-gapped setups),
construct the runtime directly with `polling=False`:

```python
from nullrun.runtime import NullRunRuntime
rt = NullRunRuntime(api_key="nr_live_...", polling=False)   # poll-only
```

This is an internal/test-only knob, not a public env var.

## See also

- [HTTP API](../reference/http-api.md#websocket-control-plane)
- [Workflow context](workflow.md)
- Kill contract (internal — available on request via
  [support@nullrun.io](mailto:support@nullrun.io))
