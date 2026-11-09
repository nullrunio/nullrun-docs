---
title: Tool policies
maturity: stable
description: The ToolBlock pattern language — the glob syntax that decides which tools an agent may call, and how patterns combine across scopes.
---

# Tool policies

A `ToolBlock` policy decides which tools the agent may call. It lives
under a policy of type **ToolBlock** — see [Policies](policies.md)
for the general overview. This page covers the pattern syntax.

## What a tool name looks like

The agent calls tools by name. The canonical name format:

| Type | Format | Example |
|---|---|---|
| Built-in tool | lowercase string | `bash`, `file_write`, `execute_code` |
| MCP tool | `mcp://{server}/{tool}` | `mcp://filesystem/read` |
| Custom tool | `custom:{name}` | `custom:my_tool` |

The matcher sees the tool name and nothing else. A rule is about
which tool runs, not what it is called with.

## Pattern syntax

`*` is the only metacharacter. `|` separates alternatives.

| Pattern | Matches | Does not match |
|---|---|---|
| `stripe.charge` | exactly `stripe.charge` | `execute_stripe.charge` |
| `send_*` | every name starting with `send_` | `resend_email` |
| `bash.*` | `bash`, `bash.foo`, `bash.foo.bar` | `bashful` |
| `*.drop_*` | `s3.drop_table` | `s3.execute_drop` |
| `bash\|sh` | `bash` or `sh` | `bashful` |
| `*` | every tool | — |

The rules behind the table:

- A pattern with no `*` is an **exact match**. It is never a
  substring match.
- A pattern with **one** `*` is an anchored prefix and/or suffix.
  `db.drop_*` matches `db.drop_table` and nothing else.
- A pattern with **two or more** `*` matches when every literal
  segment appears in the name, in order.
- `prefix.*` matches the bare prefix as well as its dotted
  continuations, so one pattern covers a whole namespace.
- `|` splits a pattern into alternatives. Each alternative is
  evaluated on its own.
- `**` matches nothing. `?` is a literal character, not a
  single-character wildcard.
- An empty pattern matches nothing.
- Matching is **case-sensitive**. Tool names are canonical lowercase,
  so `BASH` does not match `bash`.

Each entry is capped at **4096 bytes**. The cap bounds the work the
matcher does on every gate call.

## What a ToolBlock policy does

A `ToolBlock` policy **blocks** tool calls whose name matches one of
its patterns.

ToolBlock is **always hard**. It never lets a call through, whatever
the budget's `enforcement_mode` says, and it fails closed: if the
gate cannot evaluate the check, the call is refused with HTTP 403
`TOOL_BLOCKED` (SDK `error_code = "NR-T001"`). The agent never runs
an unverified sensitive operation. See
[Policies → Fail closed](policies.md#fail-closed).

There is no `action = require_approval` field on a `ToolBlock`. To
require human review first, create an **approval rule** instead —
see [Human approval](human-approval.md). The two are separate rule
objects and share no configuration schema.

The pattern list lives under the `tool_pattern` key of the policy
config. The `blocked_tools` and `tools` keys are also accepted, and
their entries join the same list. A fourth key,
`parameter_conditions`, adds argument-level conditions: such a row
blocks only when the pattern matches **and** the condition holds.

## A worked example

Suppose your agent has these tools: `tavily_search`, `send_email`,
`db.write`, `db.drop`, `stripe.charge`, `read_file`.

You want to:

- Allow read-only operations (`tavily_search`, `read_file`)
- Block destructive operations (`db.drop`, `stripe.charge`)
- Require approval for any outbound communication (`send_email`)
- Allow normal DB writes (`db.write`)

One ToolBlock policy and one approval rule:

```json title="tool_block_policy.json"
{
  "policies": [
    {
      "name": "Block destructive",
      "policy_type": "tool_block",
      "scope": "org",
      "config": {
        "tool_pattern": ["db.drop", "stripe.*"]
      }
    }
  ],
  "approval_rules": [
    {
      "name": "Outbound needs approval",
      "tool_patterns": ["send_email"],
      "action_label": "send email to customer",
      "expires_in_seconds": 300
    }
  ]
}
```

`policy_type` takes `budget_limit`, `rate_limit` or `tool_block`.
`scope` takes `org` or `workflow`. Note the two spellings: a ToolBlock
policy config uses the singular `tool_pattern`, an approval rule uses
the plural `tool_patterns`.

`send_email` triggers the approval flow — a human clicks
**Approve** in the dashboard and the call goes through. `db.drop` and
`stripe.charge` are blocked outright. The two do not interact:
ToolBlock checks and approval-rule checks are independent paths in
the gate.

## Validation at policy creation

The dashboard rejects a malformed ToolBlock config at save time with
HTTP **422** and the wire code `INVALID_FIELD`:

| Rejected | Why |
|---|---|
| A bare string instead of an array | `"tool_pattern": "send_*"` must be `"tool_pattern": ["send_*"]` |
| The plural key `tool_patterns` | The canonical key is singular: `tool_pattern` |
| An unknown key, such as `block_tools` | A typo would otherwise create a rule that blocks nothing |
| An empty pattern, or an empty config | It would match nothing, or everything |
| An entry over 4096 bytes | The per-entry byte cap |
| A pattern containing control characters | Remove `\n`, `\r`, `\t` |

## Plan gating

`ToolBlock` policies need the Custom Policies feature, which is on
**Growth+** plans. Lite and Starter can have `BudgetLimit` and
`RateLimit` policies, but not ToolBlock.

**Approval rules** are gated by the Approvals feature, which is on
Growth+ as well. On Lite and Starter the dashboard shows approval
rule creation greyed out with an **Upgrade** link, and the server
refuses the change.

## How to debug a block you didn't expect

If your agent reports `error_code = "NR-T001"` (wire `TOOL_BLOCKED`)
on a call you think should be allowed:

1. Open the workflow in the dashboard.
2. Click **Effective policy**. The merged set shows every ToolBlock
   pattern that could match.
3. Open the **Audit log** and filter by `decision = deny`. The
   **Matched rule** field names the pattern that matched.
4. If a pattern is too broad (`*` matches everything), narrow it in
   the policy editor.
5. If the pattern is wrong, deactivate the policy and re-create it
   with the correct list.

## See also

- [Policies](policies.md) — the dashboard view and the aggregation
  rules
- [Sensitive tools](sensitive-tools.md) — the policy-driven way to
  express "this tool needs review"
- [Tool catalog](../reference/llm-tool-catalog.md) — common tool
  names with risk ratings
- [Human approval](human-approval.md) — the approval-rule path,
  distinct from ToolBlock
