---
title: Sensitive tools
maturity: stable
description: How to express "this tool needs review" with ToolBlock policies and approval rules, and what a name-based rule cannot see.
---

# Sensitive tools

A **sensitive tool** is one that should never run without a human
paying attention. Sending an email, moving money, deleting a record —
these have consequences the agent cannot easily undo.

The SDK keeps a built-in set of sensitive tool names — `stripe.charge`,
`send_email`, `db.delete` and similar — and you can add your own with
`runtime.register_sensitive_tools(...)`. The set classifies names. It
blocks nothing on its own. A tool that must not run is stopped by a
server-side rule, and the gate evaluates that rule on every protected
call.

## Two mechanisms

| Mechanism | Question it answers | Outcome |
|---|---|---|
| **[ToolBlock policy](tool-policies.md)** | "May this tool run at all?" | The call is blocked. Always hard. |
| **[Approval rule](human-approval.md)** | "May this tool run this time?" | The call parks until a human approves. |

Use a ToolBlock policy for a hard rule such as "never call `bash`". Use
an approval rule when the answer depends on the call's arguments, such
as "refunds over $500 need approval".

A ToolBlock policy matches the tool name alone. It cannot tell two
calls to the same tool apart, so it over-blocks when the arguments
matter.

An approval rule matches tool patterns and adds a typed predicate over
the call's arguments. When it fires, the gate returns
`require_approval` and the SDK parks until the operator clicks Approve
or Deny. The grant is bound to a SHA-256 digest of the exact payload,
so a changed amount or changed arguments after the approval is refused.
See [Human approval → Typed predicates](human-approval.md#typed-predicates).

## What a rule cannot see

A rule matches on the canonical tool name. It does not read:

- the prompt content or the agent's intent
- the tool's runtime sandbox — that is your infrastructure's job

Two features read the arguments when you need that:

- An **approval rule** carries a typed predicate over the call's
  arguments. See
  [Human approval → Typed predicates](human-approval.md#typed-predicates).
- A **ToolBlock row** can carry `parameter_conditions`. Such a row
  blocks only when the pattern matches **and** the condition holds.
  See [Tool policies](tool-policies.md).

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

## Where to write the rule

1. Go to **Governance → Policies → New policy**.
2. Under **What kind of policy?** pick **Tool block**.
3. Enter the pattern in the **Tool pattern** field.
4. Under **Where does this apply?** pick the scope — the whole
   organization, or one workflow.

The control center shows the canonical tool name for every framework
integration, and the **Will match** line tells you which names the
pattern covers. The pattern syntax is on
[Tool policies](tool-policies.md).

Patterns **union** across every applicable policy — every pattern that
matches fires. See [Policies → Aggregation](policies.md#aggregation).

## Audit trail

A blocked sensitive tool lands in **Governance → Audit log** with the
decision `deny`, the reason code `TOOL_BLOCKED`, the pattern that
matched, the policy that matched and the tool name. The audit log is a
Growth+ feature, so Lite and Starter write no rows. The log is
hash-chained — see
[Error handling → Audit trail](error-handling.md#audit-trail).

For a sensitive tool you want to allow after human review, pair the
approval rule with the ToolBlock rule rather than dropping it from the
blocking surface. The approval row carries its own audit trail, and
the digest binds the grant to the exact payload the agent sent.

## See also

- [Tool policies](tool-policies.md) — the pattern syntax
- [Tool catalog](../reference/llm-tool-catalog.md) — recommended
  patterns with risk ratings
- [Human approval](human-approval.md) — the safer alternative to
  removing a ToolBlock rule
- [Decorators and context managers](../reference/decorators.md) — the
  `@protect` decorator and the payload it sends
