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

    A pattern is not a regular expression. Alternatives are
    separated by a pipe, and a pattern with a single wildcard
    matches both the bare name and any dotted continuation past
    it, which is what lets one pattern cover a whole server's
    namespace. A pattern with several wildcards splits on each one
    and requires the literal segments between them to appear in
    order. Matching sees the tool name and nothing else, so two
    calls to the same tool are indistinguishable at this step
    whatever their payloads.

    Patterns union across every applicable policy at both org and
    workflow scope. The most-restrictive-wins rule applies within
    a single policy type, not across types; across types the gate
    takes the first outcome other than allow in its fixed order,
    and tool blocking is evaluated ahead of budget reservation, so
    a blocked call never receives a spending envelope.

    The block is unconditional. A policy's enforcement mode does
    not soften it, and when the policy set for a key cannot be
    read, the call is treated as blocked rather than allowed —
    the trade-off is a refusal that has to be retried over a
    silent pass that goes unnoticed. Enforcement also applies on
    the cost-tracking path, so an SDK that does not declare its
    tools in the request still has the same rules applied before
    the call's cost is recorded.

    Rules that depend on arguments are a different mechanism. A
    tool block cannot inspect a refund amount or a recipient;
    that needs an approval rule with typed predicates, where the
    grant is bound to a digest of the exact payload and a later
    change to that payload invalidates the grant.
