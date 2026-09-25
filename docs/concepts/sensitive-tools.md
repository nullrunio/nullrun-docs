title: Sensitive tools
maturity: stable
description: How `@protect` plus the server-side ToolBlock policy enforce "this tool needs review" without any SDK-side sensitive list.
# Sensitive tools

A **sensitive tool** is one that should never run without a human
paying attention. Sending an email, moving money, deleting a record —
all of these have consequences the agent can't easily undo.

The way to express "this tool needs review" in NullRun is a
**[ToolBlock policy](tool-policies.md)** — a glob pattern that fails
the gate at `/gate` evaluation time, regardless of the SDK's local
context. This page covers the *recommended* patterns and how to wire
them.

!!! info "The canonical entry point is `@protect`"
    Every protected tool is automatically eligible for ToolParameters
    Approval Rules — `@protect` ships `tool_name + args + kwargs` on
    the wire, and the backend reads argument values out of `kwargs`
    by `param_name`. No SDK-side extractor or extra decorator is
    required.

!!! info "ToolBlock vs typed predicates"
    Two complementary mechanisms, often confused:

    - **`ToolBlock` (server-side)** — a policy rule evaluated by
      the gate on every `/gate` call. The gate fails-CLOSED if it
      cannot reach Redis or the policy cache to evaluate. This is
      the canonical "this tool is forbidden" mechanism.
    - **Typed predicates (`money_amount`, `tool_parameters`)** —
      built into approval rules in the dashboard. The gate
      evaluates a DNF over argument values, bound to the
      SHA-256 `action_digest` for tamper-proof approval. Use these
      for finer-grained rules ("refunds over $500 need
      approval", "sends to non-internal recipients need review").

    Use `ToolBlock` for hard rules ("never call `bash`"). Use typed
    predicates when the rule depends on the call's arguments.

## What a sensitive tool is, in policy terms

There is no built-in tool catalogue shipped by the SDK — every
enforcement decision is evaluated by the gate on every `/gate` call,
so you can't accidentally miss a tool you didn't register locally.
You express "sensitive" with one of two complementary mechanisms:

- **`@protect` (SDK-side, canonical)** — wraps a function and
  ships `tool_name + args + kwargs` on the wire. The backend
  reads argument values out of `kwargs` by `param_name` for
  ToolParameters approval rules. No SDK-side extractor is needed.
- **`ToolBlock` (server-side)** — a policy rule evaluated by the
  gate. The gate fails-CLOSED if it cannot reach Redis or the policy
  cache to evaluate. Use this for hard rules — "never call `bash`".
- **Approval rules with typed predicates (server-side)** — for
  finer-grained control, an approval rule references `param_name`
  and the gate evaluates a DNF of up to 5 named parameters against
  Equals / OneOf / NumericRange / Regex / Exists matchers. The
  grant is bound to the SHA-256 `action_digest` of the live
  payload; the post-approval `/execute` re-check refuses on
  drift.

For the typed-predicate wiring, see
[Human approval → typed predicates](human-approval.md#typed-predicates).

Recommended starter patterns (see
[Tool catalog → Recommended ToolBlock starter list](../reference/llm-tool-catalog.md#recommended-toolblock-starter-list)
for the maintained list):

| Category | Pattern examples |
|---|---|
| Money | `mcp://payments/refund*`, `mcp://stripe/charge`, `mcp://stripe/refund` |
| Email & messaging | `mcp://gmail/send`, `mcp://slack/post`, `send_email` |
| Database destructive | `mcp://postgres/drop_table`, `mcp://postgres/delete_row`, `execute_sql` |
| External API writes | `mcp://*/post`, `mcp://*/put`, `mcp://*/delete` |
| Files & storage | `mcp://s3/delete`, `file_delete`, `bash` |
| Admin | `mcp://admin/delete_user`, `mcp://admin/disable_user` |

These are the canonical tool names a policy matches against. The
**exact name** comes from your MCP server / framework integration —
see the tool catalog for the curated list with risk ratings.

## Why the SDK does not ship a built-in list

A built-in "sensitive tools" SDK list would force every framework to
register its tools against NullRun's expectations — and would be
silently wrong for any tool not on the list. The current model
inverts this:

- You write a ToolBlock policy that names the tools you care about.
- The policy is evaluated server-side on every `/gate` call.
- The decision is returned to the SDK as `TOOL_BLOCKED` (403); the SDK
  raises `NullRunToolBlockedError` with `error_code = "NR-T001"`.

The gate **does not inspect tool arguments** — it cannot distinguish
two calls to the same tool by payload. If you want a narrower rule
(e.g. "block refunds over $500"), use a typed `tool_parameters`
predicate: the SDK ships `kwargs` on the wire and the gate evaluates
a DNF of up to 5 named parameters against Equals / OneOf /
NumericRange / Regex / Exists matchers. See
[Human approval → typed predicates](human-approval.md#typed-predicates).

## Why ToolBlock is enforced at the gate

ToolBlock is enforced at the gate: sensitive operations never run
when the policy engine is unreachable. If the gate returns
`403 TOOL_BLOCKED` (SDK `error_code = "NR-T001"`), the SDK raises
before your function body executes. ToolBlock is **always Hard**,
regardless of the budget's `enforcement_mode`.

## What's NOT in a ToolBlock policy

A ToolBlock policy matches **tool name only** — not:

- prompt content or semantic intent
- the recipient of a payment (use a typed predicate instead)
- tool arguments beyond the `kwargs` the SDK ships on the wire
- the tool's runtime sandbox (that's your infrastructure concern)

Read operations are never sensitive regardless of the tool. The
canonical name alone decides.

## Where the sensitive list lives

You write the policy in the dashboard under **Policies** (sidebar
under **Governance**). Click **New policy**, pick **Tool block** as
the policy type, and the modal shows the **Tool pattern** field
where you enter the glob(s). The dashboard shows you the canonical
tool name for every framework integration. Your policy applies to:

- All workflows under the org (default)
- A specific workflow (scope to `workflow_id`)
- A specific API key (scope to `api_key_id`)

Per the [aggregation rules](../concepts/policies.md#aggregation):
ToolBlock patterns **union** across applicable policies — every
pattern that matches fires.

## Audit trail

When a sensitive tool is blocked, the **audit log** records the
block with reason `TOOL_BLOCKED` (SDK `error_code = "NR-T001"`),
the pattern that matched, and the workflow + api_key + tool_name.
The audit log is hash-chained — see
[Audit records](../concepts/error-handling.md#audit-trail).

This gives you a complete audit trail of every blocked attempt,
regardless of whether the block came from your policy or from the
default `TOOL_BLOCKED` rejection of an unknown tool name.

For sensitive tools you want to allow after explicit human review,
pair them with an **approval rule** instead of removing them from
the blocking surface. The approval row in the dashboard gives you
the audit trail, and the SHA-256 `action_digest` ensures the grant
is bound to the exact action payload the SDK sent on `/gate`. See
[Human approval](human-approval.md).

## See also

- [Tool policies](tool-policies.md) — the actual rule structure
- [Tool catalog](../reference/llm-tool-catalog.md) — recommended
  patterns with risk ratings
- [Human approval](../concepts/human-approval.md) — the safer
  alternative to disabling a ToolBlock rule
- [Decorators & context managers](../reference/decorators.md) —
  `@protect` wire payload and how the gate receives `kwargs`
- [Circuit breaker → fail-CLOSED matrix](../concepts/circuit-breaker.md#when-the-gateway-is-unreachable)

!!! info "Deep dive"

    ToolBlock lives as Step 3 of the gate orchestrator's 10-step
    priority list (`backend/src/proxy/http/gate/orchestrator.rs`,
    ADR-011). The `check_tool_block` helper reads the per-key
    `KeyPolicy.tool_patterns` cache (populated by
    `policy_cache::aggregate_policies`), then matches each pattern
    against the request's tool list using `glob_match` /
    `glob_match_single` / `glob_match_multi`. The matcher encodes
    three rules: `|` separates alternatives (`bash|sh`); a single
    `*` pattern splits into prefix + suffix where `prefix.*`
    matches both the bare name and any dotted continuation;
    multi-`*` patterns split on every `*` and require each
    non-empty literal segment to appear as a substring of `value` in
    order (the DEF-POLFLOW-TB-06 fix). When the SDK supplies
    `BusinessImpact` on `/check`, Step 4
    (`business_impact_validate`, `orchestrator.rs`) validates the
    envelope first; malformed payloads return
    `BUSINESS_IMPACT_INVALID` before any approval-rule evaluation or
    budget reservation.

    ToolBlock is ALWAYS Hard — `orchestrator.rs` codifies this:
    regardless of `enforcement_mode`, the orchestrator returns
    `Block { TOOL_BLOCKED }` whenever the helper returns a
    `ToolBlockDecision` with `decision == "block"`. The structured
    `details` JSON is forwarded verbatim, so the SDK sees the same
    wire shape pre- and post-v3.56. The orchestrator's
    policy_cache_miss path returns `TOOL_BLOCKED` if the policy
    cache has no entry for the key — fail-CLOSED, never fail-OPEN.
    The `dispatch_policy_violation_alert` bridge fires on every
    authoritative block (`orchestrator.rs`) so the operator's
    configured notification channels actually see real blocks (the
    "6 decorative toggles" audit fixed the dead bridge). The
    tool_patterns aggregate honors the per-policy scope: ToolBlock
    rows with `scope = "workflow"` MUST carry a non-NULL
    `workflow_id` (ADR-047); the three-layer invariant enforces
    this at `create_policy` validation, the `list_by_workflow` SQL
    filter, and the `is_policy_applicable_to_workflow` predicate.

    ToolBlock patterns union across applicable policies
    (`policy_aggregates.blocked_tools` is a flat dedup of every
    matching pattern). The most-restrictive-wins principle only
    applies within a single policy type; cross-policy-type the
    orchestrator steps pick the first non-Allow in priority order.
    `tool_class` annotations (`mcp` / `builtin` / `custom` /
    `unknown`) propagate from the SDK's tool catalog onto the
    `tool_policies` row in the database, so a pattern like
    `mcp://*/delete` covers every MCP server's delete tool without
    operators having to enumerate them. The SDK ships the
    `kwargs` payload on `/execute` — typed predicates in approval
    rules read values directly from there by `param_name`, no
    SDK-side extractor required.

    ToolBlock is enforced server-side in both `/check` and `/track`;
    the SDK-side enforcement (the `set_call_context(tools=[...])`
    annotation) is opt-in for early rejection.

    The chosen path is "ToolBlock is server-side, always Hard" —
    the SDK ships zero built-in sensitive-tool list because any
    such list would silently be wrong for tools not on it. The
    alternative considered was a per-SDK registration API:
    `nullrun.register_tool(name, risk=...)` — rejected because it
    would force every framework to register against NULLRUN's
    expectations, and a missed registration would be silently wrong.
    The glob matcher (`glob_match` / `glob_match_multi`) was chosen
    over a regex matcher because globs are the vocabulary operators
    see in the dashboard; the alternative considered (allow regex
    for power users) was rejected for ADR-008 scope — operators
    who want narrower predicates should use the `BusinessImpact`
    typed-predicate machinery, not a more powerful glob. The
    pre-v3.71 Step 7 stub was a regression where the
    `approval_rule_eval` arm was hardcoded to `let matched_rule =
    None` — silent fail-OPEN on operator-authored approval rules,
    fixed in v3.71 by wiring the live `evaluate_rules`
    (`enforcement/approval_eval.rs`) into the orchestrator.

    ToolBlock matches tool name only — it does not inspect tool
    arguments beyond the `kwargs` the SDK ships on `/execute`.
    Two calls to the same tool with different payloads are
    indistinguishable at the glob-match step; the narrow rule
    "block refunds over $500" requires a typed `tool_parameters`
    predicate (DNF of up to 5 named parameters against Equals /
    OneOf / NumericRange / Regex / Exists matchers). The
    orchestrator's fail-CLOSED posture on policy_cache_miss means
    that a Redis cache flush mid-traffic will surface as
    `TOOL_BLOCKED` for every `/check` until the cache repopulates —
    the trade-off is "no silent miss" over "no false positives".
    Pre-flight blocking on `/gate` is opt-in via SDK
    `set_call_context(tools=[...])`; SDKs that don't call
    `set_call_context` skip `/gate` ToolBlock enforcement
    entirely — `/track` cost-event ingestion still catches them
    downstream, but only after the LLM call has fired. ToolBlock
    patterns cannot reference `tool_class`-scoped predicates; the
    typed-predicate layer is where class-aware rules live.
