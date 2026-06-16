# NullRun

Real-time enforcement layer between AI agents and external tools
(LLMs, APIs, databases). Stops uncontrolled cost, runaway loops, and
unsafe behaviour **before** execution — not after the fact.

## What you get

- A **circuit breaker** for agents — auto-halt on cost blowups, retry
  storms, and loops
- A **policy engine** with per-workspace / per-agent / per-tool rules
- **Capability tokens** — signed, time-bounded permissions
- **Cost intelligence** — real-time + predictive attribution
- **Audit logging** — full traceability
- **Adaptive enforcement** — risk- and context-aware

## Where to start

- [Install the SDK](getting-started/install.md)
- [Quickstart](getting-started/quickstart.md)
- [Concepts](concepts/circuit-breaker.md)
- [How-to guides](how-to/langgraph.md)

## Repositories

- [`nullrunio/nullrun`](https://github.com/nullrunio/nullrun) — gateway
  server (Rust)
- [`nullrunio/nullrun-sdk-python`](https://github.com/nullrunio/nullrun-sdk-python) —
  Python SDK
- [`nullrunio/nullrun-examples`](https://github.com/nullrunio/nullrun-examples) —
  runnable examples
- [`nullrunio/.github`](https://github.com/nullrunio/.github) — org profile
  + issue templates
