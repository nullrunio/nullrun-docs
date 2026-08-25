# Sensitive tools

A **sensitive tool** is one that should never run without a human
paying attention. Sending an email, moving money, deleting a record —
all of these have consequences the agent can't easily undo.

The way to express "this tool needs review" in NullRun is a
**[ToolBlock policy](tool-policies.md)** — a glob pattern that fails
the gate at `/gate` evaluation time, regardless of the SDK's local
context. This page covers the *recommended* patterns and how to wire
them.

## What a sensitive tool is, in policy terms

There is no SDK-side built-in sensitive tool list. The shipped
behaviour is: every enforcement decision is server-side, evaluated by
the gate on every `/gate` call. You express "sensitive" with a
`ToolBlock` policy that matches the tool's canonical name.

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
(e.g. "block refunds over $500"), use a typed `BusinessImpact`
predicate: the SDK extracts the argument bag and the gate evaluates
a DNF of up to 5 named parameters against Equals / OneOf /
NumericRange / Regex / Exists matchers. See
[Human approval → typed predicates](human-approval.md#typed-predicates).

## Why ToolBlock is fail-CLOSED

Per the [Reliability matrix](../concepts/circuit-breaker.md#when-the-gateway-is-unreachable),
ToolBlock fails closed: `403 TOOL_BLOCKED` (SDK `error_code = "NR-T001"`).
Letting through a `stripe.charge` when the policy check failed means
the agent could move money without anyone knowing. The blast radius
is "agent deleted production data" or "agent leaked your data to an
attacker" — worse than a noisy stop. ToolBlock is **always Hard**,
regardless of the budget's `enforcement_mode`.

## What's NOT in a ToolBlock policy

A ToolBlock policy matches **tool name only** — not:

- prompt content or semantic intent
- the recipient of a payment (use a typed predicate instead)
- tool arguments beyond the `BusinessImpact` extraction
- the tool's runtime sandbox (that's your infrastructure concern)

Read operations are never sensitive regardless of the tool. The
canonical name alone decides.

## Where the sensitive list lives

You write the policy in the dashboard under
**Policies → Tool policies → Create**. The dashboard shows you the
canonical tool name for every framework integration. Your policy
applies to:

- All workflows under the org (default)
- A specific workflow (scope to `workflow_id`)
- A specific API key (scope to `api_key_id`)

Per the [aggregation rules](../concepts/policies.md#aggregation):
ToolBlock patterns **union** across applicable policies — every
pattern that matches fires.

## Audit trail

When a sensitive tool is blocked:

- **Decision History** records the block with reason `TOOL_BLOCKED`
  (SDK `error_code = "NR-T001"`), the pattern that matched, and the
  workflow + api_key + tool_name.
- **`audit_events`** records the decision with hash chaining — see
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
- [Human approval](human-approval.md) — the safer alternative to
  disabling a ToolBlock rule
- [Circuit breaker → fail-CLOSED matrix](../concepts/circuit-breaker.md#when-the-gateway-is-unreachable)
