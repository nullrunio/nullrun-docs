title: Tool policies
maturity: stable
description: Glob patterns for tool names with a 4 KB cap per pattern, union semantics across applicable scopes, and validation traps to avoid.
# Tool policies

A `ToolBlock` policy decides which tools the agent is allowed to call
and which it can't. In the dashboard these rules live under a policy
of type **ToolBlock** — see [Policies](policies.md) for the general
overview. This page covers how to write the patterns inside the
policy.

## Where you see it in the dashboard

When you create or edit a policy and pick **ToolBlock** as the
type, the dashboard shows a JSON editor for the `tool_pattern`,
`blocked_tools`, or `tools` array. The "Test pattern" preview at the
bottom lets you paste a tool name and see whether any pattern
matches — useful for debugging.

## What a tool name looks like

The agent calls tools by name. The canonical tool name format:

| Type | Format | Example |
|---|---|---|
| Built-in tool | lowercase string | `bash`, `file_write`, `execute_code` |
| MCP tool | `mcp://{server}/{tool}` | `mcp://filesystem/read` |
| Custom tool | `custom:{name}` | `custom:my_tool` |

The policy matcher is name-based. The SDK sends the tool name to the
gate, the gate checks it against every active ToolBlock policy, and
the verdict comes back as `allow`, `block`, or `require_approval`.

## How to write the patterns

Each entry in a ToolBlock policy is one of:

- **Exact name** — `"stripe.charge"` blocks only that one tool.
- **Glob** — `"send_*"` blocks anything starting with `send_`.
- **`*` alone** — blocks everything.

Each entry is capped at **4096 bytes**. The cap exists because the
matcher scans every pattern on every gate call — a 10 MB pattern
would burn CPU on each call.

The matcher runs case-insensitively against the canonical tool name.

## What a ToolBlock policy does

A ToolBlock policy **blocks** tool calls whose name matches one of
its patterns. There is no `action = require_approval` field on a
ToolBlock — for "I want a human to approve before this tool runs",
create an **approval rule** instead (see
[Human approval](human-approval.md)). The two are separate entities
on the backend (`policies` vs `approval_rules`).

ToolBlock is **always Hard**: it never lets through, regardless of
the budget's `enforcement_mode`. See
[Reliability matrix](../concepts/circuit-breaker.md#when-the-gateway-is-unreachable).
If the gate cannot evaluate the ToolBlock check (Redis or policy
cache unavailable), it fails closed — `403 TOOL_BLOCKED` (SDK
`error_code = "NR-T001"`). The agent never runs an unverified
sensitive operation.

## A worked example

Suppose your agent has these tools: `tavily_search`, `send_email`,
`db.write`, `db.drop`, `stripe.charge`, `read_file`.

You want to:

- Allow read-only operations (`tavily_search`, `read_file`)
- Block destructive operations (`db.drop`, `stripe.charge`)
- Require approval for any outbound communication (`send_email`)
- Allow normal DB writes (`db.write`) but block `db.drop`

Two ToolBlock policies and one approval rule:

```json title="tool_block_policy.json"
{
  "policies": [
    {
      "name": "Block destructive",
      "type": "ToolBlock",
      "scope": "Org",
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

`send_email` now triggers the approval flow (a human clicks
**Approve** in the dashboard before the call goes through). `db.drop`
and `stripe.charge` are blocked outright. The two policies do not
interact — ToolBlock checks and approval-rule checks are independent
paths in the gate.

## Validation at policy creation

The dashboard rejects invalid patterns at save time:

| Error | Cause | Fix |
|---|---|---|
| `400 bare_string_pattern` | `"pattern": "send_*"` instead of `"pattern": ["send_*"]` | Always use an array, even for one entry |
| `400 pattern_too_long` | An entry longer than the per-pattern byte cap | Split into multiple patterns |
| `400 invalid_glob` | Contains control characters | Remove `\n`, `\r`, `\t` |

## Plan gating

`ToolBlock` policies require the Custom Policies feature, which is
on **Growth+** plans. Lite and Starter can have `BudgetLimit` and
`RateLimit` policies, but not ToolBlock.

On Lite / Starter, the dashboard shows ToolBlock policy creation
greyed out with an "Upgrade" link.

## How to debug a block you didn't expect

If your agent reports `error_code = "NR-T001"` (wire `TOOL_BLOCKED`) on
a call you think should be allowed:

1. Open the workflow in the dashboard.
2. Click **Effective policy**. The merged set shows every ToolBlock
   pattern that could match.
3. Click **Decision History** and filter by `decision = block` and
   the tool name. The audit log shows which pattern matched.
4. If a pattern is too broad (`*` matches everything), narrow it
   in the policy editor.
5. If the pattern is wrong entirely, deactivate the policy and
   re-create it with the correct list.

## See also

- [Policies](policies.md) — the dashboard view, aggregation rules,
  and most-restrictive-wins semantics
- [Sensitive tools](sensitive-tools.md) — the policy-driven way to
  express "this tool needs review" (not a built-in SDK list)
- [Tool catalog](../reference/llm-tool-catalog.md) — common tool
  names with risk ratings
- [Human approval](human-approval.md) — the approval-rule path,
  distinct from ToolBlock
