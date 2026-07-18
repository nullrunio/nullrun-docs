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

The agent calls tools by name. Each framework uses its own
convention, but the SDK normalises them to `snake_case`:

| Framework | Tool name in the SDK | Example |
|---|---|---|
| LangChain | toolkit function name | `tavily_search`, `sql_db_query` |
| OpenAI hosted | OpenAI tool id | `code_interpreter` |
| MCP server | `mcp://server/tool` | `mcp://filesystem/read` |
| Custom | `custom:{name}` | `custom:my_internal_api` |

The policy matcher is name-based. The SDK sends the tool name to the
gate, the gate checks it against every active ToolBlock policy, and
the verdict comes back as `allow`, `block`, or `require_approval`.

## How to write the patterns

Each entry in a ToolBlock policy is one of:

- **Exact name** — `"stripe.charge"` blocks only that one tool.
- **Prefix glob** — `"send_*"` blocks anything starting with
  `send_`.
- **Suffix glob** — `"_test"` blocks anything ending with `_test`.
- **Prefix-suffix glob** — `"send_*_test"` blocks anything starting
  with `send_` and ending with `_test`.
- **`*` alone** — blocks everything.

The matcher is case-insensitive. `stripe.charge`, `STRIPE.CHARGE`,
and `Stripe.Charge` are the same name to the matcher.

Only one `*` is allowed per pattern. `a*b*c` is interpreted as
"starts with `a`, ends with `c`" — anything in between is fine.

## What's blocked by default

The SDK ships a built-in **sensitive** list that always blocks,
regardless of your policies. See [Sensitive tools](sensitive-tools.md)
for the full list and how to extend it. Your ToolBlock policy is
**in addition** to the built-in defaults — you can make things
stricter, never looser.

## A worked example

Suppose your agent has these tools: `tavily_search`, `send_email`,
`db.write`, `db.drop`, `stripe.charge`, `read_file`.

You want to:

- Allow read-only operations (`tavily_search`, `read_file`)
- Block destructive operations (`db.drop`, `stripe.charge`)
- Require approval for any outbound communication (`send_email`)
- Allow normal DB writes (`db.write`) but block `db.drop`

Three policies:

```json title="tool_block_policy.json"
{
  "policies": [
    {
      "name": "Block destructive ops",
      "type": "ToolBlock",
      "scope": "Org",
      "config": {
        "tool_pattern": ["db.drop", "stripe.*", "send_*"]
      }
    },
    {
      "name": "Require approval for outbound",
      "type": "ToolBlock",
      "scope": "Org",
      "config": {
        "tool_pattern": ["send_*"],
        "action": "require_approval"
      }
    }
  ]
}
```

When the agent calls `send_email`, the gate sees two matches: the
"Block" pattern and the "Require approval" pattern. Most-restrictive
wins — **block** beats **require approval**. You typically want one
rule per tool category, not overlapping.

A cleaner version:

```json title="tool_block_policy_clean.json"
{
  "name": "Outbound needs approval",
  "type": "ToolBlock",
  "scope": "Org",
  "config": {
    "tool_pattern": ["send_*", "post_*"],
    "action": "require_approval"
  }
},
{
  "name": "Block destructive",
  "type": "ToolBlock",
  "scope": "Org",
  "config": {
    "tool_pattern": ["db.drop", "stripe.charge", "stripe.refund"]
  }
}
```

Now `send_email` triggers the approval flow (a human clicks
**Approve** in the dashboard before the call goes through). See
[Human approval](human-approval.md) for the operator experience.

## Validation at policy creation

The dashboard rejects invalid patterns at save time:

| Error | Cause | Fix |
|---|---|---|
| `400 bare_string_pattern` | `"pattern": "send_*"` instead of `"pattern": ["send_*"]` | Always use an array, even for one entry |
| `400 pattern_too_long` | An entry longer than 4096 bytes | Split into multiple patterns |
| `400 invalid_glob` | Contains control characters | Remove `\n`, `\r`, `\t` |

The 4096-byte cap exists because the matcher scans every pattern
on every gate call. A 10 MB pattern would burn CPU on each call.

## Plan gating

`ToolBlock` policies require `CustomPolicies`, which is on
**Growth+** plans. Lite and Starter can have BudgetLimit and
RateLimit policies, but not ToolBlock.

On Lite / Starter, the dashboard shows ToolBlock policy creation
greyed out with an "Upgrade" link.

## How to debug a block you didn't expect

If your agent reports `TOOL_BLOCKED` on a call you think should be
allowed:

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

- [Sensitive tools](sensitive-tools.md) — built-in defaults
- [Policies](policies.md) — the dashboard view
- [Tool catalog](../reference/llm-tool-catalog.md) — common tool
  names with risk ratings
- [Human approval](human-approval.md) — the `require_approval` action
