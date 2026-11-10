---
title: Tool policies
maturity: stable
description: The ToolBlock pattern language — the glob rules that decide which tool names an agent may not call, and how a tool block behaves at the gate.
---

# Tool policies

A `ToolBlock` policy blocks tool calls by name. It is one of three
policy types — see [Policies](policies.md) for the general overview.
This page is the reference for the pattern language and for the config
keys.

## What a tool name looks like

The agent calls tools by name, and the gate matches the canonical name.
Three shapes exist:

| Type | Format | Example |
|---|---|---|
| Built-in tool | lowercase string | `bash`, `file_write`, `execute_code` |
| MCP tool | `mcp://{server}/{tool}` | `mcp://filesystem/read` |
| Custom tool | `custom:{name}` | `custom:my_tool` |

A built-in name is lowercase ASCII letters, digits, `_` and `-`, up to
64 characters. The server part of an MCP name follows the same rule,
and the tool part may contain slashes. A custom name is non-empty and
at most 64 characters.

The matcher sees the name and nothing else. A rule is about which tool
runs, not what it is called with.

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

- A pattern with no `*` is an **exact match**. It is never a substring
  match.
- A pattern with **one** `*` is an anchored prefix and/or suffix.
  `db.drop_*` matches `db.drop_table` and nothing else.
- A pattern with **two or more** `*` matches when every literal segment
  appears in the name, in order. The start stays anchored when the
  pattern does not begin with `*`, and the end when it does not end
  with `*`.
- `prefix.*` matches the bare prefix as well as its dotted
  continuations, so one pattern covers a whole namespace.
- `|` splits a pattern into alternatives. Each alternative is evaluated
  on its own.
- `**` matches nothing. `?` is a literal character, not a
  single-character wildcard.
- An empty pattern matches nothing.
- Matching is **case-sensitive**. Tool names are canonical lowercase,
  so `BASH` does not match `bash`.

Each entry is capped at **4096 bytes**. The cap bounds the work the
matcher does on every gate call.

## The config

A ToolBlock policy carries its patterns under one of three keys. The
three join the same list:

| Key | Value |
|---|---|
| `tool_pattern` | An array of pattern strings |
| `blocked_tools` | An array of pattern strings |
| `tools` | An array of pattern strings |

A fourth key, `parameter_conditions`, adds an argument-level
condition. Such a row blocks only when the pattern matches **and** the
condition holds, and its patterns stay out of the unconditional pattern
list. The control center offers two modes for it: **Any matching call** and
**Match specific parameters**.

## What a block does

ToolBlock always blocks. A `ToolBlock` policy has no soft mode, and
the server refuses an `enforcement_mode` on it with HTTP 422.

If the gate cannot evaluate the check, the call is refused with HTTP
403 `TOOL_BLOCKED` and the SDK raises `NullRunToolBlockedError`
(`error_code = "NR-T001"`). The protected body does not run. See
[Policies → Fail closed](policies.md#fail-closed).

To put a human in the loop instead of blocking, use an approval rule.
See [Human approval](human-approval.md).

## A worked example

Suppose the agent has these tools: `tavily_search`, `send_email`,
`db.write`, `db.drop`, `stripe.charge`, `read_file`.

You want to allow the read-only tools and the normal database write,
and to block the destructive ones:

```json title="tool_block_policy.json"
{
  "name": "Block destructive tools",
  "policy_type": "tool_block",
  "scope": "org",
  "config": {
    "tool_pattern": ["db.drop", "stripe.charge"]
  }
}
```

`policy_type` takes `budget_limit`, `rate_limit` or `tool_block`.
`scope` takes `org` or `workflow`. A workflow-scoped policy also
carries `workflow_id`.

The stored config is an array of patterns. The control center's **Tool
pattern** field is a single text box, so it writes one element and
separates the alternatives with `|`:

```json
{
  "tool_pattern": ["db.drop|stripe.charge"]
}
```

Both forms block the same set of tools.

## Validation at policy creation

The server rejects a malformed ToolBlock config with HTTP **422** and
the wire code `VALIDATION_FAILED`:

| Rejected | Why |
|---|---|
| A bare string instead of an array | `"tool_pattern": "send_*"` must be `"tool_pattern": ["send_*"]` |
| The plural key `tool_patterns` | The canonical key is singular: `tool_pattern` |
| An unknown key, such as `block_tools` | A typo would otherwise create a rule that blocks nothing |
| An empty pattern, or an empty config | A rule that blocks nothing |
| `parameter_conditions` with no tool pattern | The condition narrows an existing tool scope, it does not define one |
| An entry over 4096 bytes | The per-entry byte cap |
| A pattern containing control characters | Remove `\n`, `\r`, `\t` |

## Plan gating

`ToolBlock` policies are available on every plan. They draw on the
same per-organization quota as every other policy and as approval
rules — see [Policies → Plan gating](policies.md#plan-gating).

**Approval rules** are a separate feature and are gated on Growth+.

## How to debug a block you didn't expect

If the agent reports `error_code = "NR-T001"` (wire `TOOL_BLOCKED`) on
a call you think should be allowed:

1. Open the workflow and go to the **Policies** tab. The **Effective
   controls** card shows every ToolBlock pattern that could match.
2. Open the policy in the editor. The **Will match** line lists the
   tool names a pattern covers.
3. Open **Governance → Audit log** and filter by `decision = deny`. The
   event detail has a **Matched rule** field. It reads `policy.block`
   for a blocked tool, so the row does not name the pattern.
4. If a pattern is too broad, narrow it in the editor.
5. To take a rule out of service, turn the policy's **Active** toggle
   off. The policy stays in the list.

## See also

- [Policies](policies.md) — the control center view, the aggregation rules
  and the fail-closed table
- [Sensitive tools](sensitive-tools.md) — when to block and when to ask
  a human
- [Tool catalog](../reference/llm-tool-catalog.md) — common tool names
  with risk ratings
- [Human approval](human-approval.md) — the approval-rule path,
  distinct from ToolBlock
