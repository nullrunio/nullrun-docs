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
rows in migration `002_plans.sql` (with the `060_fix_plan_limits`
rebalance applied to Lite / Starter / Growth / Scale). Enterprise is
unlimited on every dimension.

| Plan | Workflows | Executions / month | History | Team seats | API keys | Policies | Overage |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **Lite** | 3 | 500 | 1 day | 1 | 10 | 1 | not allowed |
| **Starter** | 10 | 5,000 | 7 days | 3 | 25 | 5 | not allowed |
| **Growth** | 50 | 50,000 | 30 days | 10 | 100 | 15 | allowed (1.5×) |
| **Scale** | 150 | 1,500,000 | 90 days | 50 | 250 | 100 | not allowed |
| **Enterprise** | unlimited | unlimited | unlimited | unlimited | unlimited | unlimited | contract |

> If the database is unreachable, the gateway falls back to the
> in-code Phase 136 rebalance (75K / 250K / 500K / 1M / unlimited).
> On startup `assert_db_matches_code` aborts the process if the DB
> drifts from this table — see
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
