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

- **Breaker** — cost control + circuit breaker (the flagship)
- **Gate** — tool / action security (policy-bound execution)
- **Flow** — durable workflow runtime with retry, pause, resume
- **Vault** — secrets + signed credentials for agent-side calls
- **Trace** — execution telemetry and audit log
- **Policy** — declarative rules with first-match-wins composition
- **Signal** — anomaly detection on agent behaviour

## Plans

There is **no time-limited trial**. The **Lite** plan is permanently
free with hard limits (3 workflows, 500 executions/month, 1-day
history, 1 team seat, no overage). Pro and Enterprise are paid plans
with the same surface — no feature gating behind a trial state.

## Where to start

- [Install the SDK](getting-started/install.md)
- [Quickstart](getting-started/quickstart.md)
- [Concepts](concepts/circuit-breaker.md)
- [How-to guides](how-to/langgraph.md)

## Repositories

- [`nullrunio/nullrun`](https://github.com/nullrunio/nullrun) — gateway
  (Rust, crate `breaker-core`) and frontend (`breaker-dashboard`)
- [`nullrunio/nullrun-sdk-python`](https://github.com/nullrunio/nullrun-sdk-python) —
  Python SDK (`pip install nullrun`)
- [`nullrunio/nullrun-examples`](https://github.com/nullrunio/nullrun-examples) —
  runnable examples
- [`nullrunio/nullrun-docs`](https://github.com/nullrunio/nullrun-docs) —
  this documentation site (https://docs.nullrun.io)
- [`nullrunio/.github`](https://github.com/nullrunio/.github) — org profile
  + issue templates
