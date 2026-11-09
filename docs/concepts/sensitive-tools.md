---
title: Sensitive tools
maturity: stable
description: How to express "this tool needs review" with ToolBlock patterns and approval rules — NullRun ships no SDK-side list of sensitive tools.
---

# Sensitive tools

A **sensitive tool** is one that should never run without a human
paying attention. Sending an email, moving money, deleting a record —
these have consequences the agent cannot easily undo.

NullRun ships **no SDK-side list of sensitive tools** and no decorator
that marks a function as sensitive. A built-in list would be silently
wrong for every tool it does not name. You express sensitivity with
server-side rules instead, and the gate evaluates them on every
protected call.

Two mechanisms, and they answer different questions:

| Mechanism | Question it answers | Outcome |
|---|---|---|
| **[ToolBlock policy](tool-policies.md)** | "May this tool run at all?" | The call is blocked. Always hard, fails closed. |
| **[Approval rule](human-approval.md)** | "May this tool run this time?" | The call parks until a human approves. |

Use ToolBlock for hard rules such as "never call `bash`". Use an
approval rule when the answer depends on the call's arguments, such
as "refunds over $500 need approval".

## The two rules in detail

### ToolBlock — hard, by tool name

A ToolBlock policy is a list of glob patterns over the canonical tool
name. The gate matches the name against every active policy and
blocks on a hit. It never inspects the arguments, so it cannot tell
two calls to the same tool apart.

ToolBlock is always hard and fails closed: if the gate cannot
evaluate the check, the call is refused with HTTP 403
`TOOL_BLOCKED` (SDK `error_code = "NR-T001"`) and your function body
does not run.

### Approval rules — soft, by tool name and arguments

An approval rule matches tool patterns and adds a typed predicate
over the call's arguments. When it fires, the gate returns
`require_approval` and the SDK parks until the operator clicks
Approve or Deny. The grant is bound to a SHA-256 digest of the exact
payload, so a changed amount or changed arguments after the approval
is refused. See
[Human approval → Typed predicates](human-approval.md#typed-predicates).

## Recommended starter patterns

The exact name comes from your MCP server or framework integration.
See the
[tool catalog](../reference/llm-tool-catalog.md#recommended-toolblock-starter-list)
for the maintained list with risk ratings.

| Category | Pattern examples |
|---|---|
| Money | `mcp://payments/refund*`, `mcp://stripe/charge`, `mcp://stripe/refund` |
| Email and messaging | `mcp://gmail/send`, `mcp://slack/post`, `send_email` |
| Database destructive | `mcp://postgres/drop_table`, `mcp://postgres/delete_row`, `execute_sql` |
| External API writes | `mcp://*/post`, `mcp://*/put`, `mcp://*/delete` |
| Files and storage | `mcp://s3/delete`, `file_delete`, `bash` |
| Admin | `mcp://admin/delete_user`, `mcp://admin/disable_user` |

## What a ToolBlock rule does not match

A ToolBlock rule sees the tool name only. It does not match:

- prompt content or semantic intent
- the recipient of a payment
- any argument beyond the name
- the tool's runtime sandbox — that is your infrastructure's job

A read-only operation needs no special treatment. The canonical name
alone decides.

## Where to write the rule

You write the policy in the dashboard under **Governance → Policies**.
Click **New policy**, pick **Tool block**, and enter the pattern(s)
in the **Tool pattern** field. The dashboard shows the canonical tool
name for every framework integration.

A policy applies to:

- every workflow under the organization, by default
- one workflow, scoped to it

Patterns **union** across every applicable policy — every pattern that
matches fires. See
[Policies → Aggregation](policies.md#aggregation).

## Audit trail

When a sensitive tool is blocked, the **audit log** records the block.
The row carries the decision `deny`, the reason code `TOOL_BLOCKED`,
the pattern that matched, the policy that matched and the tool name.
The log is hash-chained — see
[Error handling → Audit trail](error-handling.md#audit-trail).

For a sensitive tool you want to allow after human review, pair the
approval rule with the ToolBlock rule rather than dropping it from
the blocking surface. The approval row carries its own audit trail,
and the digest binds the grant to the exact payload the agent sent.

## See also

- [Tool policies](tool-policies.md) — the pattern syntax
- [Tool catalog](../reference/llm-tool-catalog.md) — recommended
  patterns with risk ratings
- [Human approval](human-approval.md) — the safer alternative to
  removing a ToolBlock rule
- [Decorators and context managers](../reference/decorators.md) — the
  `@protect` decorator and the payload it sends
