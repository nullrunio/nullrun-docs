# Control plane (WebSocket)

> **Current contract:** v3 (SDK ≥ 0.12.0, server ≥ 1.0.0).
> The WS push catalog below is current. The `policy_invalidated`
> and `key_rotated` events are server-driven — the SDK does not
> poll for them.

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

The SDK implements the canonical message catalog from
`nullrun.transport_websocket.WebSocketConnection`. Server →
client types are dispatched by string equality on the `type`
field; unknown types are logged at WARNING with a counter bump
(`unknown_ws_message_type_total`) so an SRE can alert on a forward-
compat break.

Server → client message types:

| Type | When | SDK reaction |
| --- | --- | --- |
| `initial_state` | First message after subscribe; full per-workflow state snapshot (list of workflow dicts) | Dispatch each workflow entry to `on_state_change` (signed entries are parsed from `signed_payload` so the inner fields are trusted, not the outer envelope) |
| `state_change` | A workflow's state flipped (Normal / Flagged / Tripped / Killed / Paused). Requires `ack` for `Killed` / `Paused` only. | Dispatch to `on_state_change`. For `Killed`/`Paused` the SDK sends an HMAC-signed `ack` with the `message_id` before invoking the callback. |
| `policy_invalidated` | A policy in your workspace changed (saved via the dashboard); cached decisions must be re-evaluated | Drop cached policy decisions; next gate call re-evaluates. Callback signature: `(organization_id, policy_id, new_version)`. |
| `key_rotated` | The HMAC secret for an API key was rotated; cached auth state must be refreshed | Refresh cached credentials; next call uses the new key. Callback signature: `(organization_id, key_id, new_version)`. |
| `approval_resolved` | A pending human-approval request was approved or denied by an operator. Carries `approval_id`, `workflow_id`, `execution_id`, `outcome` (`approved`/`denied`), optional `note`, `resolved_at`. | On `approved`, release the gate reservation so the agent resumes on the same `execution_id`. On `denied`, surface `WorkflowKilledInterrupt`. Callback signature: `(full_message_dict)`. |
| `resync_required` | Server overflowed its broadcast channel; client must drop local state and re-fetch | Close + reconnect (per ADR-007). Server publishes a fresh `initial_state` after reconnect. |
| `subscribed` | Subscription confirmation (carries `organization_id`) | Logged at DEBUG; no SDK action. |
| `pong` | Heartbeat reply to client `ping` | Logged at DEBUG; no SDK action. |
| `error` | Server-side protocol error (`code` + `message`) | Logged at WARNING; no SDK action. |
| *(unknown)* | Forward-compat: a `type` the SDK does not recognise | Logged at WARNING with the payload keys, counter incremented. **Not** a reconnect trigger. |

Client → server:

| Type | When | Notes |
| --- | --- | --- |
| `ack` | Generic ack for any server message that requires one (carries `message_id`, `received_at`, HMAC signature) | Sent only for `Killed`/`Paused` `state_change` messages today. HMAC-signed via the same `generate_hmac_signature` helper the HTTP transport uses, so a future server-side ACK verifier needs no client-side wire change. |

## How the SDK reacts

| Server message | SDK action |
| --- | --- |
| `state_change` (killed) | Raise `WorkflowKilledInterrupt` on the next gate call. If a call is currently mid-execution, the interrupt is queued and raised at the next yield point. |
| `state_change` (paused) | Raise `WorkflowPausedException` on the next gate call. |
| `policy_invalidated` | Drop cached policy decisions; the next gate call re-evaluates. |
| `key_rotated` | Refresh cached credentials; the next call uses the new key. |
| `approval_resolved` (approved) | Release the gate reservation so the agent resumes on the same `execution_id` without polling `/status`. |
| `approval_resolved` (denied) | Surface `WorkflowKilledInterrupt` on the next gate call. |
| `resync_required` | Drop local workflow / policy state and re-fetch from `/api/v1/orgs/{org_id}/status`. |

The kill contract (see `docs/kill-contract.md` in the gateway repo)
defines which events are recoverable vs terminal.

## Operator UI

The dashboard's **Workflows → `<workflow_id>` → Actions** panel sends
`state_change` messages. `policy_invalidated` is sent automatically
when a policy is saved. `key_rotated` is sent when an API key's
HMAC secret is rotated (via
`POST /api/v1/orgs/{org_id}/api-keys/{key_id}/rotate`, **not** on
key revocation/delete). `approval_resolved` is sent when a
pending human-approval request is approved or denied by an operator
(see [Concepts → Human approval](human-approval.md)).

## When the WebSocket is down

If the WS endpoint is blocked by your network (corporate firewall,
proxy in the way, etc.) the SDK falls back to HTTP polling on
`/api/v1/orgs/{org_id}/workflows/{workflow_id}` — a 1-second round trip
that surfaces kill/pause with at most 1s of latency.

!!! info "No public env var for transport mode"
    There is **no** `NULLRUN_TRANSPORT` env var. Earlier docs drafts
    mentioned one; it was never wired up to the SDK. To force HTTP
    polling from start (instead of letting WS push fail over), build
    a `NullRunRuntime` directly:

    ```python title="polling_runtime.py"
    from nullrun.runtime import NullRunRuntime

    runtime = NullRunRuntime(api_key="nr_live_...", polling=True)
    ```

    In practice the SDK is correct to keep this internal — selecting
    the transport at runtime is a deploy-time concern, not a config
    knob you want to flip per-request.

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
