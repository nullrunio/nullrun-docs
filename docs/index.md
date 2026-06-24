# NullRun

Enforcement platform for AI agents — a set of products that let
teams ship agents without losing control of cost, scope, or behaviour.

## What you get

- A **circuit breaker** for agents — auto-halt on cost blowups, retry
  storms, and loops (`@protect` gate)
- A **policy layer** with per-workspace / per-agent / per-tool rules
  (first-match-wins composition — ADR-007)
- **Signed capability tokens** — time-bounded, HMAC-SHA256 permissions
  for sensitive tool calls
- **Cost intelligence** — real-time attribution + per-workflow
  budget + `time-to-exhaustion` (single-call status endpoint:
  `GET /api/v1/orgs/{org_id}/status`)
- **Audit logging** — full traceability
- **Adaptive enforcement** — risk- and context-aware detectors

## Products

NullRun is layered as seven cooperating subsystems. The names below
are a navigation aid, not a marketing taxonomy — each one maps to a
real module in the gateway.

- **Breaker** — cost control + circuit breaker (the flagship). Implemented
  in `proxy/middleware/` and `enforcement/`. Halt triggers: budget cap,
  loop, rate, sensitive-tool.
- **Gate** — the `@protect` enforcement point. Every `track_llm` /
  `track_tool` call from the SDK flows through `proxy/handlers.rs` →
  `enforcement/decision_engine.rs`. Returns allow / block / require-approval.
- **Flow** — durable workflow runtime. `execution/state_machine.rs`
  + control-plane `StateChange` over `WS /ws/control/{org_id}`. Supports
  kill / pause / resume at any gate call.
- **Identity** — HMAC-SHA256 signed capability headers. Replaces
  client-side secrets: the SDK signs every request with `NULLRUN_SECRET_KEY`,
  the gateway verifies the signature. **NULLRUN never stores customer
  LLM API keys** — credentials stay in your environment.
- **Trace** — execution telemetry + audit log. `observability/` +
  `events/` + `proxy/middleware/metrics.rs`. Surfaces token counts,
  cost, latency, and policy decisions per workflow.
- **Policy** — declarative rules with first-match-wins composition.
  `policy/` + `proxy/policy_cache.rs`. Per-org / per-agent / per-tool
  scopes (see ADR-007).
- **Detectors** — adaptive enforcement. `detectors/` runs loop / rate
  / drift / retry-storm analysis on the event stream and feeds
  signals back to the Gate.

## Plans

There is **no time-limited trial**. The **Lite** plan is permanently
free with hard caps; the rest are paid. Plan limits are enforced
from the `plans` table at runtime — the values below mirror the seed
rows in migration `002_plans.sql` after the full migration chain
(`060_fix_plan_limits`, `136_plan_rebalance_v2`,
`137_plan_seats_per_tier`, `159_scale_tier_rebalance`,
`161_plan_config_defensive_reset`, `170_disable_overage_all_plans`,
`171_plan_tier_rebalance_2026_06_24`). Enterprise is unlimited on
every dimension.

| Plan | Workflows | Executions / month | History | Team seats | API keys | Policies | Overage |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **Lite** | 3 | 75,000 | 3 days | 1 | 10 | 1 | not allowed |
| **Starter** | 8 | 100,000 | 7 days | 3 | 15 | 3 | not allowed |
| **Growth** | 50 | 750,000 | 30 days | 10 | 100 | 25 | not allowed |
| **Scale** | 200 | 2,000,000 | 90 days | 75 | 350 | 150 | not allowed |
| **Enterprise** | unlimited | unlimited | unlimited | unlimited | unlimited | unlimited | not allowed |

Overage billing is **disabled on every tier** (migration 170,
2026-06-24). Growth previously allowed overage at 1.5× and Enterprise
at contract pricing — both flipped to hard caps until the
metered-overage model is finalized. If you hit a cap, the gateway
returns 422 `plan_limit_exceeded` (see [Error codes](docs/reference/errors.md)).

> If the database is unreachable, the gateway falls back to the
> in-code Phase 136 rebalance (75K / 250K / 500K / 1M / unlimited
> for Lite / Starter / Growth / Scale / Enterprise — note Scale
> here is 1M, **not** 2M; the in-code fallback was not updated
> alongside migration 171, so it lags the DB by one rebalance).
> On startup `assert_db_matches_code` aborts the process if the DB
> drifts from the in-code `Entitlements` mirror — see
> [[scale-plan-not-unlimited]](https://github.com/nullrunio/nullrun-docs)
> in the engineering notes.

## Where to start

- [Install the SDK](getting-started/install.md)
- [Quickstart](getting-started/quickstart.md)
- [Concepts](concepts/circuit-breaker.md)
- [How-to guides](how-to/langgraph.md)

## Repositories

- [`nullrunio/nullrun-sdk-python`](https://github.com/nullrunio/nullrun-sdk-python) —
  Python SDK (`pip install nullrun`)
- [`nullrunio/nullrun-examples`](https://github.com/nullrunio/nullrun-examples) —
  runnable examples
- [`nullrunio/nullrun-docs`](https://github.com/nullrunio/nullrun-docs) —
  this documentation site (https://docs.nullrun.io)
- [`nullrunio/.github`](https://github.com/nullrunio/.github) — org profile
  + issue templates

The NullRun gateway and dashboard live in a private repository.
Access is granted on request via [support@nullrun.io](mailto:support@nullrun.io).
