# Budgets

A budget is a hard cap on cost for a single workflow run. When the
budget is exceeded, the workflow is halted and the agent stops.

## How budgets are enforced (v3 wire contract)

The SDK 0.12.0+ ships a **two-call v3 contract** against the
gateway: one `/gate` call to pre-flight and mint a reservation,
then one `/api/v1/track` (single-event) call to commit the actual
cost. The legacy three-call flow (`/check` + `/execute` +
`/track`) was deprecated in SDK 0.12.0 and removed for new code
paths in 0.13.1.

1. **Pre-flight + reservation `/api/v1/gate`** — on every
   `@protect`-wrapped call, the SDK asks the gateway "is there any
   budget left?" with the projected cost. The gateway evaluates
   the policy (budget + tool-block + sensitive-tool + loop
   detection) and, if it approves, **mints a server-side
   `reservation_id` (uuidv7)** keyed to the workflow + chain. The
   response carries `reservation_id`, the reserved `cents`, and a
   `policy_snapshot`. This is binary: the gateway either reserves
   the projected cost or rejects the call with a structured
   `error` slug.

   The SDK caches the `reservation_id` for ~295s via the
   `_server_minted_execution_id` contextvar; subsequent
   `track_event` / `track_llm` calls during the same `@protect`
   block carry it on the wire so the server can match the commit
   back to the reservation.

2. **Commit `/api/v1/track` (single event)** — when the LLM call
   completes, the SDK reports the actual cost via the v3
   single-event endpoint, including `reservation_id` (the gate's
   uuidv7) and `idempotency_key` (the `/gate` call's
   `operation_id`). The gateway either **commits** the reservation
   (real cost ≤ reserved + ε) or **releases** the unused
   reservation if the actual cost was lower. Cumulative spend is
   updated from committed reservations + reconciled `cost_events`.

   On retry of the same event (network blip, transport flush
   retry), the same `idempotency_key` lands twice; the gateway
   dedups by key and returns the original commit result. A
   *different* `idempotency_key` on the same `reservation_id`
   returns `409 idempotency_key_hash_mismatch` — the SDK treats
   this as a recoverable error and retries with a fresh key.

The pre-flight is the source of truth for the policy decision; the
post-flight `/track` reconciles drift between projected and actual
cost.

!!! info "Legacy endpoints"
    `/api/v1/check` was removed in SDK 0.13.1 — it now returns
    `410 Gone` with `replacement: /api/v1/gate`. New integrations
    should target `/gate` directly. `/api/v1/execute` is still
    registered on the gateway for legacy callers but the SDK no
    longer emits traffic against it.

## Set a budget

In the NullRun dashboard, open a workflow and set the per-workflow
budget. Or via the API:

```bash title="set_budget.sh"
curl -X PATCH https://api.nullrun.io/api/v1/orgs/$ORG_ID/workflows/$WORKFLOW_ID \
  -H "X-API-Key: $NULLRUN_API_KEY" \
  -H "X-Signature: $(compute_hmac)" \
  -H "X-Signature-Timestamp: $(date +%s)" \
  -H "Content-Type: application/json" \
  -d '{"budget_cents": 500}'
```

Inside `@protect`, set the workflow id via `nullrun.workflow(...)`
(the decorator itself takes no kwargs):

```python title="budgeted_workflow.py"
import nullrun
from nullrun import init, protect

init(api_key="nr_live_...")

with nullrun.workflow("my-workflow"):
    @protect
    def step(): ...
```

Once set, any call inside that workflow context stops the moment
cumulative committed cost exceeds 500¢. The SDK raises
`NullRunBudgetError` (a `NullRunBlockedException` subclass,
`error_code="NR-B004"`) for budget-exhausted decisions, and the
generic `NullRunBlockedException` (`NR-X001`) for other policy
blocks (tool-blocked, sensitive-tool, loop detection).

## Per-call cap

The SDK does not project per-call cost on its own — the per-call
cap is enforced by the workspace policy on the gateway. When the
policy carries a `max_per_call_cents` limit, `/gate` rejects any
single call whose projected cost would exceed the cap *before* the
model is invoked. The SDK surfaces this as `NullRunBlockedException`
with `.reason="per_call_cap"`.

## v3 protocol negotiation

On `init()`, the SDK calls `GET /api/v1/capabilities` to confirm
the backend supports the v3 contract (`server_minted_execution_id`
+ `per_execution_reservations` + `heartbeat_time_based`). If the
backend reports v3-ready but the SDK is older than `0.12.0`,
`init()` emits a startup warning so the operator sees the gap
before the first `/gate` call fails with `400 PROTOCOL_TOO_OLD`.
The canonical `SDK_MIN_VERSION_FOR_V3` constant lives in
`nullrun.capabilities` and is the gate the backend enforces.

To opt out of v3 single-event routing entirely (e.g. against a
v1/v2-only backend), set `NULLRUN_V3_TRACK_DISABLE=1` and the SDK
falls back to the legacy `/track/batch` path. This is rarely
needed in production — every shipped 1.0.0 backend supports v3.

## See also

- [Circuit breaker](circuit-breaker.md)
- [How-to → Set a hard cost cap](../how-to/cost-cap.md)
- [Errors](../reference/errors.md)
- [HTTP API → SDK endpoints](../reference/http-api.md#sdk-endpoints)
- [HTTP API → Capabilities](../reference/http-api.md#capabilities)
