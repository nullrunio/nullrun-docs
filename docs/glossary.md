---
title: Glossary
description: Every NullRun term in one place — gate, policy, budget, execution_id, reservation, approval rule, and the fail-closed contract.
maturity: stable
---

# Glossary

The vocabulary NullRun uses, in one place. Each entry says what the
term means and links to the page that goes deeper on it.

## Enforcement

**Gate**
:   The check that runs before a supported tool or model call executes.
    It returns one of three decisions — `allow`, `block`, or
    `require_approval` — and it is the only thing standing between an
    agent's intent and its side effects. See
    [Circuit breaker](concepts/circuit-breaker.md).

**Policy**
:   A rule attached to your organization or to a single workflow. Each
    policy answers one enforcement question, and the applicable ones
    are aggregated most-restrictive-wins across scopes. There are three
    types — `budget_limit`, `rate_limit`, and `tool_block`. See
    [Policies](concepts/policies.md).

**ToolBlock**
:   The policy type that decides which tools an agent may call. Its
    patterns are glob matches over canonical tool names, unioned across
    every scope that applies. It is **always hard**: a transport error
    refuses the call regardless of the budget's `enforcement_mode`. See
    [Tool policies](concepts/tool-policies.md).

**Sensitive tool**
:   A tool that should never run without a human paying attention —
    sending mail, moving money, deleting a record. The SDK keeps a
    registry of common sensitive tool names, but the registry enforces
    nothing. Sensitivity is enforced by server-side rules: `ToolBlock`
    patterns and approval rules. See
    [Sensitive tools](concepts/sensitive-tools.md).

**Fail-closed / fail-open**
:   What happens when the gate cannot get the signal it needs. On the
    gateway the enforcement path fails **closed**: a failure to evaluate
    the budget or the per-organization rate limit refuses the call. In
    the SDK the tool-policy gate also fails
    **closed**, so a protected body does not run when the policy engine
    cannot be reached. Two SDK checks fail **open**: the budget
    pre-flight skips the check and logs a warning when the gateway is
    unreachable, then corrects the spend in the tracked events, and the
    control-plane check treats an unreachable gateway as a normal
    workflow. See [Policies](concepts/policies.md) and
    [Circuit breaker](concepts/circuit-breaker.md).

**Circuit breaker**
:   The SDK-side guard that short-circuits event flushes after repeated
    infrastructure failures, so an unreachable gateway does not turn
    into a hang. It opens on transport errors and closes again after a
    cooldown. It does not sit on the gate path, and a protected call is
    never blocked by it. See [Circuit breaker](concepts/circuit-breaker.md).

**Protocol version**
:   The wire contract version the SDK sends on every gateway request in
    the `X-NULLRUN-PROTOCOL` header. The SDK sends version `4`. The
    gateway refuses a request whose version it does not support. See
    [HTTP API](reference/http-api.md).

## Cost

**Budget**
:   The maximum a workflow may spend in one period. Amounts are in
    cents. See [Budgets](concepts/budgets.md).

**Enforcement mode**
:   Whether a budget blocks hard or soft. `Hard` refuses the call once
    the projected cost exceeds what is left. `Soft` allows a bounded
    overdraft, but only when all three hold: the policy is set to
    `Soft`, an active `chain_id` exists, and the cost stays inside the
    overdraft cap. The cap is the lower of `max_overdraft_cents` and
    `max_overdraft_percent`. When the cap is exhausted the chain is
    marked exhausted and further `Soft` calls on it are refused. See
    [Budgets](concepts/budgets.md).

**execution_id**
:   The id the gateway mints for one tool call. It is a UUIDv7, so ids
    sort by time, and the gateway — not the client — issues it. The
    gateway binds it to your organization and API key, so a call can
    only be settled by the identity that reserved it. See
    [HTTP API](reference/http-api.md).

**Reservation**
:   The amount a workflow commits at gate time, before the call runs.
    The actual cost is consumed against it afterwards, so the reserve /
    consume invariant keeps a single call from being implicitly
    re-reserved. See [Budgets](concepts/budgets.md).

**Consume**
:   The settlement of a reservation after the call runs. The consumed
    amount may not exceed the reserved amount plus a small fixed
    tolerance. A call that overshoots is refused. See
    [Budgets](concepts/budgets.md).

**operation_id**
:   The id the SDK attaches to one gate call, so several calls in the
    same scope stay distinguishable from one another. It is a client
    value and carries no authority of its own. See
    [HTTP API](reference/http-api.md).

## Runtime

**Workflow**
:   One agent you run. Each workflow carries its own budget, its own API
    keys, and its own policies, and its cost binds to it as a logical
    unit rather than to a single session. See
    [Workflow context](concepts/workflow.md).

**Chain**
:   A group of workflows that run as one logical unit under a shared
    chain context, so a kill or an overrun surfaces across the rest. A
    chain that exceeds its max duration is rejected by the gate with
    `CHAIN_MAX_DURATION_EXCEEDED`. See
    [Workflow context](concepts/workflow.md).

**Action**
:   One concrete operation an agent wants to perform — a tool call or a
    model call, with its arguments. The unit the gate evaluates and the
    unit an approval is bound to. See
    [Human approval](concepts/human-approval.md).

**Action source**
:   The gateway's name for one MCP server (or built-in provider) the SDK
    has talked to. One row in **Governance → Action Sources**. See
    [MCP servers](concepts/mcp-servers.md).

**Trace**
:   Everything that happened during one run of your agent: every LLM
    call, every tool call, and how long each took. See
    [Tracing](concepts/tracing.md).

**Span**
:   One node in a trace — a single LLM or tool call, with its timing and
    its correlation ids. Spans nest, and a parent trace id propagates
    across a workflow so the control center renders a true waterfall. See
    [Tracing](concepts/tracing.md).

## Control

**Approval**
:   A human decision that lets one specific action run. The grant is
    bound to the exact action payload through a SHA-256
    `action_digest`; if the payload drifts, the grant is refused. See
    [Human approval](concepts/human-approval.md).

**Approval rule**
:   A rule that asks for a human instead of answering `allow` or
    `block` on its own. It is not a fourth policy type: it sits beside
    the policies and matches tool patterns plus a predicate over the
    call's business impact — an amount of money, or a named argument
    value. Approval rules are separate from `ToolBlock`: the tool block
    says which tools are off limits, the approval rule says which calls
    need a person. See [Human approval](concepts/human-approval.md).

**action_digest**
:   The SHA-256 hash that binds an approval to the action it approves.
    A digest mismatch after approval produces a hard block rather than
    letting the substituted action through. See
    [Human approval](concepts/human-approval.md).

**Control plane**
:   The WebSocket channel between the control center and your running agent.
    It is what makes **Kill**, **Pause**, and **Resume** take effect
    immediately rather than on the next gate call. See
    [Control plane](concepts/control-plane.md).

**Kill**
:   The control-plane signal that stops a workflow. It arrives as
    `WorkflowKilledInterrupt`, which inherits from `NullRunError`
    directly — it is not a policy decision, so
    `except NullRunDecision` does not catch it. See
    [Error handling](concepts/error-handling.md).

**Pause**
:   The control-plane signal that suspends a workflow. It surfaces as
    `WorkflowPausedException` carrying an optional `resume_after`. A
    gate call to a paused workflow is refused with `403`
    `WORKFLOW_PAUSED`. See
    [Error handling](concepts/error-handling.md).
