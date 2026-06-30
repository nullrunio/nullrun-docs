# Control plane (WebSocket)

The control plane is a real-time channel between the NullRun gateway
and connected SDKs. It carries the events that need to land at the
agent **while it is running** — kill / pause decisions, policy
changes, key rotations, and full-state resyncs.

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

Server → client message types:

| Type | When |
| --- | --- |
| `InitialState` | First message after subscribe; full per-workflow state snapshot |
| `StateChange` | A workflow was killed, paused, or resumed (requires `Ack` for pause/kill) |
| `PolicyInvalidated` | A policy in your workspace changed (saved via the dashboard); cached decisions must be re-evaluated |
| `KeyRotated` | The HMAC secret for an API key was rotated; cached auth state must be refreshed |
| `Subscribed` | Subscription confirmation (sent after the SDK subscribes) |
| `ResyncRequired` | Server asks the client to drop local state and re-fetch |
| `Error` | Protocol error |
| `Pong` | Heartbeat reply |

Client → server:

| Type | When |
| --- | --- |
| `Ack` | Generic ack for any server message that requires one (carries `message_id` for `StateChange`) |

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
a policy is saved. `KeyRotated` is sent when an API key's HMAC secret
is rotated (via `POST /api/v1/orgs/{org_id}/api-keys/{key_id}/rotate`,
**not** on key revocation/delete).

## When the WebSocket is down

The SDK supports two transport modes for the control plane
(selected via `NULLRUN_TRANSPORT`):

- `ws` (default) — WebSocket push to `/ws/control/{org_id}`.
  Sub-second kill/pause propagation. On disconnect the SDK
  reconnects with exponential backoff.
- `http` — 1-second polling fallback. Each poll round fetches
  per-workflow state from
  `GET /api/v1/orgs/{org_id}/workflows/{workflow_id}` (not
  `/status` — that route is the legacy pre-Phase-139 path that no
  longer exists). Use this in environments where the WS endpoint is
  blocked.

The control-plane check on every `@protect` gate entry merges the
local cached remote state with whatever the transport last delivered.
A WS push and a `@protect` call can run concurrently — a kill that
arrives between two gate calls lands before the next call (no lost
state window).

## See also

- [HTTP API](../reference/http-api.md#websocket-control-plane)
- [Workflow context](workflow.md)
- Kill contract (internal — available on request via
  [support@nullrun.io](mailto:support@nullrun.io))
