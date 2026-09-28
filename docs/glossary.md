---
title: Glossary
description: Every NullRun term in one place — gate, policy, budget, workflow, span, action source, approval, and the fail-closed contract — with a link to the page that explains each one.
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
    are aggregated most-restrictive-wins across scopes. The four types
    are `BudgetLimit`, `RateLimit`, `ToolBlock`, and
    `LoopDetection`. See [Policies](concepts/policies.md).

**ToolBlock**
:   The policy type that decides which tools an agent may call. Its
    patterns are glob matches over canonical tool names, unioned across
    every scope that applies. It is **always hard**: it fails closed on
    a transport error regardless of the budget's
    `enforcement_mode`. See [Tool policies](concepts/tool-policies.md).

**Sensitive tool**
:   A tool that should never run without a human paying attention —
    sending mail, moving money, deleting a record. NullRun does not
    ship a built-in list of these; you express them as `ToolBlock`
    patterns. See [Sensitive tools](concepts/sensitive-tools.md).

**Fail-closed / fail-open**
:   What the gate does when it cannot reach the policy engine.
    `ToolBlock` and aggregate rate limiting fail **closed** (the call is
    refused) because the policy is the authoritative gate; per-key rate
    limits and budget checks fail **open** because the budget
    enforcement layer behind them is the real backstop. See
    [Policies](concepts/policies.md).

**Circuit breaker**
:   The SDK-side guard that short-circuits gate calls after repeated
    infrastructure failures, so an unreachable gateway does not turn
    into a hang. It opens on transport errors and closes again after a
    cooldown. See [Circuit breaker](concepts/circuit-breaker.md).

## Cost

**Budget**
:   The maximum a workflow may spend in one billing period. Amounts are
    in cents. See [Budgets](concepts/budgets.md).

**Enforcement mode**
:   Whether a budget blocks hard or soft. `Hard` refuses the call once
    the projected cost exceeds what is left. `Soft` allows a bounded
    overdraft, but only when all three hold: the policy is set to
    `Soft`, an active `chain_id` exists, and the cost stays inside both
    `max_overdraft_cents` and `max_overdraft_percent`. The chain
    returns to Hard mode once the cap is exhausted. See
    [Budgets](concepts/budgets.md).

**Reservation**
:   The amount a workflow commits at gate time, before the call runs.
    The actual cost is consumed against it afterwards, so the reserve /
    consume invariant keeps a single call from being implicitly
    re-reserved. See [Budgets](concepts/budgets.md).

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
    across a workflow so the dashboard renders a true waterfall. See
    [Tracing](concepts/tracing.md).

## Control

**Approval**
:   A human decision that lets one specific action run. The grant is
    bound to the exact action payload through a SHA-256
    `action_digest`; if the payload drifts, the grant is refused. See
    [Human approval](concepts/human-approval.md).

**action_digest**
:   The SHA-256 hash that binds an approval to the action it approves.
    A digest mismatch after approval produces a hard block rather than
    letting the substituted action through. See
    [Human approval](concepts/human-approval.md).

**Control plane**
:   The WebSocket channel between the dashboard and your running agent.
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
    `WorkflowPausedException` carrying a `resume_after`, and maps to
    HTTP `503` with a `Retry-After` header. See
    [Error handling](concepts/error-handling.md).
