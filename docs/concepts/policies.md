title: Policies
maturity: stable
description: How BudgetLimit, RateLimit, ToolBlock, and LoopDetection policies are aggregated — most-restrictive-wins semantics across scopes.
# Policies

A **policy** is a rule attached to your organization or a single
workflow. In the dashboard they live under **Governance → Policies**.
Each policy answers one question:

- "Is this call allowed, blocked, or does it need a human to approve?"

## What you see in the dashboard

The **Policies** page lists every policy in your org. Each row
shows:

- **Name** — you set this when you created the policy
- **Type** — what the policy caps (see the table below)
- **Scope** — applies to the whole org, or only one workflow
- **Active** toggle — on/off without deleting
- **Effective from** — when the policy was last edited

Click a policy to edit it. Changes apply to the next gate call —
there's no need to redeploy your agent.

## The three policy types

| Type | What it controls | Example value |
|---|---|---|
| **BudgetLimit** | Maximum spend per workflow per period | `5000` ($50.00) |
| **RateLimit** | Maximum calls per minute | `60` (one call per second sustained) |
| **ToolBlock** | Tools the agent must not call | `["send_*", "db.drop", "stripe.charge"]` |

Each type has a JSON config payload — see the [Tool policies](tool-policies.md)
page for the glob-match syntax inside `ToolBlock`.

## BudgetLimit — extra fields

A `BudgetLimit` policy can carry these optional fields:

| Field | Default | What it does |
|---|---|---|
| `enforcement_mode` | `"Hard"` | `Hard` blocks on budget exceeded. `Soft` allows a bounded overdraft when an active chain is present. |
| `max_overdraft_cents` | `0` | Maximum overdraft in cents (per-org aggregate). Both `cents` and `percent` apply — the lower cap wins. |
| `max_overdraft_percent` | `0` | Maximum overdraft as percent of the budget. |
| `max_chain_duration_seconds` | `3600` | Maximum duration of a chain started under this policy before the gate refuses. |

The gate reads these fields from every applicable `BudgetLimit` and
uses **most-restrictive-wins**: `enforcement_mode` (Hard > Soft),
`max_overdraft_cents` (min), `max_overdraft_percent` (min).

### Soft mode requirements

Soft mode requires **all three**:

1. The policy uses `enforcement_mode = Soft` (not Hard)
2. An **active `chain_id`** exists (declared via `with chain(...)`)
3. The projected cost stays within `max_overdraft_cents` and
   `max_overdraft_percent`

If any of the three is missing, soft mode is unavailable and the
gate behaves as Hard. Multiple parallel chains on the same org share
one overdraft counter — N concurrent chains do **not** multiply the
overdraft cap.

A chain dies on the first of: `op="end"`, 5 minutes of `/gate`
inactivity (idle TTL), or exceeding `max_chain_duration_seconds`.
Chain time is read server-side, eliminating clock skew between
backend nodes.

## Aggregation

When two policies in the merged set compete, the engine picks the
**most restrictive** one for numeric caps and the **union** for tool
patterns.

| Field | If two policies disagree |
|---|---|
| `budget_cents` | The smaller number wins |
| `max_calls_per_minute` | The smaller number wins |
| `enforcement_mode` | `Hard` beats `Soft` |
| `max_overdraft_cents` | The smaller number wins |
| `max_overdraft_percent` | The smaller number wins |
| `tool_pattern` / `blocked_tools` / `tools` | Both lists are merged (a tool blocked anywhere is blocked everywhere) |

You can't accidentally un-block a tool the org blocks. There is no
"allow" rule that overrides a "block" — the system is conservative
on purpose.

## Org-level vs workflow-level

A policy has one of two scopes:

- **Org** — applies to every workflow in your organization. Useful
  for "all our agents must block `db.drop`" or "everyone gets 60
  calls/min".
- **Workflow** — applies to one workflow only. Useful for "this
  specific agent gets $500/month" or "this one agent can call
  `send_email`".

Both scopes apply at the same time. There's no "overrides" — both
sets of rules run together. The dashboard's **Effective policy** tab
on a workflow page shows the merged set.

## Templates

The dashboard ships with **templates** — pre-built policies for
common patterns. To enable one:

1. On the **Policies** page, click **Templates**.
2. Pick a template (e.g. "Cap dev workflow at 100c/min" or "Block
   all write tools").
3. Click **Enable**.

The template materialises as a real policy in your org using its
config and name. Disable reverses it. Templates save you from
hand-authoring JSON.

## Plan gating

Some policy features are plan-restricted:

| Feature | Available on |
|---|---|
| `BudgetLimit` policies | All plans |
| `RateLimit` policies | All plans |
| `ToolBlock` policies | Growth+ |
| Approval rules with typed predicates | Growth+ |

If you try to create a feature your plan doesn't include, the
dashboard shows the feature greyed out with an "Upgrade" link.

## Approval rules — separate from ToolBlock

Approval rules are **not** a `ToolBlock` policy with an `action =
require_approval` field. They are a separate rule object with
`tool_patterns`, a projected-cost threshold, a typed `BusinessImpact`
predicate, and operational metadata.

When a rule fires, the gate returns `decision = "require_approval"`
and the SDK parks until the operator clicks Approve / Deny. See
[Human approval](human-approval.md) for the full flow, the typed
`action_digest` binding, and the WebSocket push resume path.

## How to create one

1. **Governance → Policies → New policy**.
2. Pick the type (BudgetLimit / RateLimit / ToolBlock).
3. Pick the scope (Org or specific workflow).
4. Fill in the config. The dashboard validates the JSON in real
   time and shows errors before you save.
5. Save. The policy is active immediately.

<figure class="nr-shot">
  <img class="nr-shot__light" src="../../assets/images/screenshots/policies-list-light.png"
       alt="Policies list with the New policy button highlighted in the top right.">
  <img class="nr-shot__dark" src="../../assets/images/screenshots/policies-list-dark.png"
       alt="Policies list with the New policy button highlighted in the top right.">
  <figcaption class="nr-shot__caption">Governance · Policies · New policy</figcaption>
</figure>

To test a new policy before rolling it out broadly, scope it to
one workflow. The dashboard's **Effective policy** tab on that
workflow's detail page shows the merged result so you can see exactly
what your agent will see.

## What gets logged

Every policy decision is recorded in **Governance → Audit log**.
You can filter by:

- Workflow
- Decision type (`allow` / `block` / `require_approval`)
- Time window
- Tool name (for `ToolBlock` matches)

The audit log is the source of truth for "why did my agent stop
working at 14:32 yesterday?". Pair it with [Traces](tracing.md) to
see the exact request that triggered the decision.

## See also

- [Tool policies](tool-policies.md) — the `ToolBlock` matching rules
- [Budgets](budgets.md) — how `BudgetLimit` interacts with the
  period rollover
- [Human approval](human-approval.md) — typed `BusinessImpact` rules
  that produce `require_approval`
- [Workflows](workflow.md) — where the merged policy is applied

## Deep dive

### Mechanism

`aggregate_policies` at `backend/src/proxy/policy_cache.rs` is
the single source of truth for the gate's merged view. It iterates
the `policies` table once, applies per-type reduction: `BudgetLimit`
→ `min()` on `config.budget_cents` (split by scope into
`budget_cents` / `wf_budget_cents` / `org_budget_cents`); `RateLimit`
→ `min()` on `max_calls_per_minute`; `ToolBlock` → union across
`tool_pattern` / `blocked_tools` / `tools` arrays (HashSet-backed
dedup, O(M+N) amortized since v3.52). The result lands on a
`KeyPolicy` per `(org_id, api_key_id)` and is read on every gate call.
ADR-011 §"Decision priority" orders the orchestrator at
`run_gate_orchestrator` (`backend/src/proxy/http/gate/orchestrator.rs`)
as `Block > RequireApproval > Allow`: workflow_active → parent_ownership
→ cycle_depth_check (ADR-036) → tool_block (TB-1/TB-4 fail-CLOSED) →
business_impact_validate → rate_limit → budget_reserve. The first
non-`Allow` short-circuits the rest. Soft mode is folded into
BudgetLimit via three preconditions (`enforcement_mode=Soft`, active
chain, projected within `max_overdraft_cents` AND
`max_overdraft_percent`); when any precondition is missing the gate
behaves as Hard.

### Guarantees

There is no "allow rule that overrides a block" — the system is
conservative on purpose (CLAUDE.md §"There is no allow rule that
overrides a block"). ToolBlock is always Hard regardless of
`enforcement_mode`: the orchestrator's Step 3 runs before the budget
reserve, so a blocked tool never gets a budget envelope minted.
Approval rules are a SEPARATE rule object — they do NOT share the
ToolBlock config schema and have no `action = require_approval` field
on a ToolBlock policy. Aggregator ordering is deterministic
(``aggregate_policies` runs synchronously on policy refresh and writes
into the cache before the gate sees the new state). Per-org aggregate
rate limit (ADR-029 §2) is Hard / FailClosed; per-key is FailOpen with
the budget gate as the authoritative backstop. ADR-049 (policy
aggregator enforcement mode) restricts `enforcement_mode` aggregation
to BudgetLimit only — ToolBlock and RateLimit do not carry
`enforcement_mode`, so they cannot accidentally flip a Soft BudgetLimit
to Hard.

### Patterns

Both scopes apply at the same time (no "overrides"). The dashboard's
**Effective policy** tab calls `workflows.rs::aggregate_policies`
which delegates to the same `policy_cache::aggregate_policies` —
single source of truth, so the operator-visible merged set can never
drift from the gate's view. Per-key cap `KeyPolicy.max_budget_cents`
defaults to 0 (= no per-key budget → fall through to the org plan
cap), and `wf_budget_cents: Option<u64>` preserves the
`None`/`Some(0)`/`Some(n)` semantics: `None` means "no policy applies,
skip wf check"; `Some(0)` is a hard zero ceiling that rejects every
call; `Some(n)` enforces the cap. The Rust `execute_with_degraded()`
helper on `RedisCircuitBreaker` / `PostgresCircuitBreaker` (ADR-055)
wraps every gate hot-path site so an infra partition short-circuits
sub-100ms instead of hanging 5–10s on `pool.acquire()`.

### Approaches

The pre-2026-06-27 gate used a legacy `PolicyEvaluationGraph` /
`PolicyNode` scoring machinery that silently dropped `rate_limit` and
`tool_block` configs and read budget from the wrong column
(`policies.budget_cents` = 1000 default vs `config.budget_cents` =
user-configured value). The direct
`check_tool_block → budget check → Lua reservation` pipeline replaced
it. Approval rules were originally scoped to be a `ToolBlock` policy
field — rejected because the two have distinct config schemas (a
ToolBlock config has no typed `BusinessImpact` predicate); approval
rules live in their own table. ADR-029 §2 considered making per-key
rate-limit fail-CLOSED — rejected as over-restrictive (budget gate is
the authoritative backstop; per-key rate-limit is a secondary signal).
Percentage-based ε was considered for `max_overdraft_percent` —
rejected for the abuse surface; the fixed-cents cap (default 1¢) is
applied after percentage is multiplied by `max_budget_cents` and the
two are min'd (CLAUDE.md §"max_overdraft").

### Limitations

The aggregator cannot unblock a tool the org blocks — by design.
There is no "allow rule" precedence; unions only. `ToolBlock` policies
are gated to **Growth+** plans (Lite / Starter cannot create them) — the
gate enforces `approval_rules = 0` server-side on Lite / Starter
(even if a key was minted on a higher tier and downgraded, rules are
retained for audit but no new rule can be created). The aggregator's
split-budget tracking (`wf_budget_cents` / `org_budget_cents` /
`policy_org_ceiling_cents`) carries Option semantics end-to-end — a
refactor that collapses `None` → `0` (sentinel collapse) silently
re-opens the silent fail-OPEN trap where `wf_budget = 0` was treated
as "no policy" instead of "hard zero" (locked decision 1, ADR-016
§2.10). The cache's `entry_version` field guards against split-brain:
a write with a stale `policy_version` is rejected as cache miss
(CLAUDE.md §31).
