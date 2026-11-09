---
title: Policies
maturity: stable
description: How BudgetLimit, RateLimit and ToolBlock policies work — their fields, how the engine combines them across scopes, and what happens when a check fails.
---

# Policies

A **policy** is a rule attached to your organization or to a single
workflow. In the control center they live under **Governance → Policies**.

## What you see in the control center

The **Policies** page lists every policy in your org. Each row shows:

- **Name** — what you set when you created the policy
- **Type** — what the policy caps
- **Config** — a preview of the cap or the pattern
- **Scope** — the whole org, or one workflow
- **Active** — a toggle that turns the policy on and off without
  deleting it
- **Threshold** — the effective cap the policy contributes

Click a policy to edit it. A change applies to the next gate call.

## The three policy types

| Type | Wire name | What it controls | Example value |
|---|---|---|---|
| **BudgetLimit** | `budget_limit` | Maximum spend per period | `5000` ($50.00) |
| **RateLimit** | `rate_limit` | Maximum calls per minute | `60` (one call per second, sustained) |
| **ToolBlock** | `tool_block` | Tools the agent must not call | `["send_*", "db.drop", "stripe.charge"]` |

Each type carries a JSON config payload. The pattern syntax inside a
`ToolBlock` config is on [Tool policies](tool-policies.md).

## BudgetLimit — extra fields

A `BudgetLimit` policy can carry these optional fields at the top level of
the body:

| Field | Default | What it does |
|---|---|---|
| `enforcement_mode` | `"Hard"` | `Hard` blocks on budget exceeded. `Soft` allows a bounded overdraft when an active chain is present. |
| `max_overdraft_cents` | `0` | Maximum overdraft in cents. The cent cap and the percent cap both apply — the lower one wins. |
| `max_overdraft_percent` | `0` | Maximum overdraft as a percentage of the budget. |
| `max_chain_duration_seconds` | `3600` | Stored on the policy. The gate ends a chain after one hour and does not read this field. |

The gate reads these fields from every applicable `BudgetLimit` and
uses **most-restrictive-wins**: `enforcement_mode` (Hard beats
Soft), `max_overdraft_cents` (min), `max_overdraft_percent` (min).

`enforcement_mode`, `max_overdraft_cents` and `max_overdraft_percent` are
BudgetLimit-only. The server refuses them with HTTP 422 when you create
a `RateLimit` or `ToolBlock` policy.

`BudgetLimit` also reads `consume_epsilon_cents` from its config. It
is the tolerance between the amount reserved for a call and the amount
the call is charged. It defaults to 1 cent, and the smallest value
across the applicable policies wins.

### Soft mode requirements

Soft mode needs all three of these:

1. The policy uses `enforcement_mode = Soft` and is scoped to a
   **workflow**. The server refuses Soft mode on an
   organization-scope policy with HTTP 422.
2. An **active chain** exists — declared with `with chain(...)`.
3. The projected cost stays inside both `max_overdraft_cents` and
   `max_overdraft_percent`.

If one of the three is missing, the budget behaves as Hard. Parallel
chains on one organization share a single overdraft allowance, so
concurrency does not multiply the cap.

A chain ends on the first of: `op="end"`, five minutes without a gate
call, or one hour of chain lifetime.

## Aggregation

When two applicable policies disagree, the engine takes the **most
restrictive** numeric cap and the **union** of the tool patterns.

| Field | If two policies disagree |
|---|---|
| `budget_cents` | The smaller org-scope number wins, and the smaller workflow-scope number wins. The two caps stay apart because each is measured against its own counter. |
| `max_calls_per_minute` | The smaller number wins, per scope. |
| `enforcement_mode` | `Hard` beats `Soft` |
| `max_overdraft_cents` | The smaller number wins |
| `max_overdraft_percent` | The smaller number wins |
| `consume_epsilon_cents` | The smaller number wins |
| `tool_pattern` / `blocked_tools` / `tools` | Both lists merge — a tool blocked anywhere is blocked everywhere |

You cannot un-block a tool that another scope blocks. There is no
"allow" rule that overrides a "block".

A `ToolBlock` row that carries `parameter_conditions` blocks only when
the pattern matches **and** the condition holds. Its patterns stay out
of the unconditional pattern list.

## Org-level vs workflow-level

A policy has one of two scopes:

- **Organization** — applies to every workflow in your organization.
  Use it for rules like "all our agents must block `db.drop`".
- **Workflow** — applies to one workflow. Use it for rules like
  "this agent gets $500 per period".

Both scopes apply together. There is no override. The **Policies** tab
on a workflow page shows the merged set under **Effective controls**.

## Templates

The control center ships **templates** — pre-built policies for common
patterns:

1. On the **Policies** page, open **Templates**.
2. Pick a template.
3. Click **Activate**.

A template materialises as a real policy in your org. Activating it
again turns it off.

## Plan gating

| Feature | Available on |
|---|---|
| `BudgetLimit` policies | All plans |
| `RateLimit` policies | All plans |
| `ToolBlock` policies | All plans |
| Approval rules | Growth+ |
| Audit log | Growth+ |

Policies and approval rules share one quota per organization:

| Plan | Policies and approval rules |
|---|---|
| Lite | 3 |
| Starter | 10 |
| Growth | 25 |
| Scale | 150 |
| Enterprise | Unlimited |

If you try to use a feature your plan does not include, the control center
shows it greyed out with an **Upgrade** link, and the server refuses
the change.

## Fail closed

Every check on the enforcement path **refuses** when it cannot be
evaluated. A refusal is a refusal, not a pass.

| Situation | Result |
|---|---|
| The gateway cannot be reached | The protected body does not run. A network failure raises `NullRunBlockedException` with `NR-B001`, a gateway 5xx raises `NullRunBlockedException` with `NR-B002`, and a rejected key raises `NullRunAuthError` with `NR-A003`. |
| The rate-limit store cannot be reached | The call is refused with HTTP 503 `RATE_LIMIT_REDIS_UNAVAILABLE`. |
| The budget store cannot be reached | The call is refused with HTTP 402 `BUDGET_REDIS_UNAVAILABLE`. |
| A `ToolBlock` policy cannot be evaluated at the gate | The call is refused with HTTP 403 `TOOL_BLOCKED`. |
| A `ToolBlock` policy cannot be evaluated at the track backstop | The call is refused with HTTP 503 `TOOL_BLOCKED_BACKSTOP_UNAVAILABLE`. |

The SDK's own circuit breaker is the single local exception. After
repeated transport failures it stops calling the gateway and keeps
the pending work on disk. See
[Circuit breaker](circuit-breaker.md).

The rate limiter keeps two buckets: one per key and one per
organization. Both can refuse on their own, and both read the same
store, so a store outage refuses with 503
`RATE_LIMIT_REDIS_UNAVAILABLE`.

## Approval rules — separate from ToolBlock

Approval rules are not a `ToolBlock` policy with an
`action = require_approval` field. They are a separate rule object
with `tool_patterns`, a projected-cost threshold, a typed
`BusinessImpact` predicate and operational metadata.

When a rule fires, the gate returns `decision = "require_approval"`
and the SDK parks until the operator clicks Approve or Deny. See
[Sensitive tools](sensitive-tools.md) for how to choose between the
two, and [Human approval](human-approval.md) for the approval flow.

## How to create one

1. **Governance → Policies → New policy**.
2. Pick the type (**Budget**, **Rate limit** or **Tool block**).
3. Pick the scope (**Organization** or one **Workflow**).
4. Fill in the config. The control center validates the JSON and shows the
   errors, so you can fix them.
5. Save. The policy is active immediately.

<figure class="nr-shot">
  <img class="nr-shot__light" src="../../assets/images/screenshots/policies-list-light.png"
       alt="Policies list with the New policy button highlighted in the top right."
       loading="lazy" decoding="async">
  <img class="nr-shot__dark" src="../../assets/images/screenshots/policies-list-dark.png"
       alt="Policies list with the New policy button highlighted in the top right."
       loading="lazy" decoding="async">
  <figcaption class="nr-shot__caption">Governance · Policies · New policy</figcaption>
</figure>

To test a policy, scope it to one workflow. The **Policies** tab of
that workflow shows the merged result.

## What gets logged

On Growth and above, every policy decision lands in **Governance →
Audit log**. Filter by decision (`allow`, `deny`, `require_approval`),
event type, actor and time window.

Lite and Starter do not include the audit log, so no decision rows are
written for them.

The audit log answers "why did my agent stop working at 14:32?".
Pair it with [Traces](tracing.md) to see the request behind the
decision.

## See also

- [Tool policies](tool-policies.md) — the `ToolBlock` pattern rules
- [Budgets](budgets.md) — how a `BudgetLimit` interacts with the
  period rollover
- [Sensitive tools](sensitive-tools.md) — blocking a tool against
  asking a human
- [Human approval](human-approval.md) — rules that produce
  `require_approval`
- [Workflows](workflow.md) — where the merged policy applies
