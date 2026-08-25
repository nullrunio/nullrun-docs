# NullRun

NullRun is a runtime decision layer for tool-using AI agents. Before an
agent executes a supported tool or model call, the SDK sends a
structured request to the gate. The gate evaluates applicable policies
and runtime state, then returns `allow`, `block`, or `require_approval`.
The SDK or calling application must honor that decision.

**Managed runtime control plane. Not a self-hosted deployment.**

## What you get

- A **gate** for every agent action — `@protect`-decorated functions
  flow through `/api/v1/gate` before execution
- **Tool-pattern policies** — glob-match tool names, route sensitive
  calls through human approval or block outright
- **Budget enforcement** — hard limit by default, soft mode available
  when an active `chain_id` exists with a configured overdraft cap
- **Action-bound approvals** — typed `BusinessImpact` predicates
  (`money_amount` / `tool_parameters`) bound by SHA-256 `action_digest`.
  The grant is refused on `/execute` if the action payload changed
- **Rate limiting** — token bucket per subject (per-key fails open,
  aggregate fails closed)
- **Audit trail** — every decision logged with budget snapshot,
  chain state, and decision path

## Where to start

- [Install the SDK](getting-started/install.md)
- [Quickstart](getting-started/quickstart.md)
- [Concepts](concepts/circuit-breaker.md)
- [How-to guides](how-to/langgraph.md)

## Trust boundary

NullRun evaluates structured action requests before execution. It does
not inspect prompts, tool arguments, or model output semantics. Cost
enforcement relies on SDK-reported estimates and usage — a malicious
SDK that controls its own cost reports is not protected by the gate.

The SDK is Python-only. TypeScript, JavaScript, and Go do not have
equivalent runtime SDKs (a generator script produces low-level HTTP
clients only). The control plane (policies, approvals, audit, billing,
team) is reachable via the dashboard, not via the SDK.

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
