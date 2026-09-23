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

<figure class="nr-shot">
  <img class="nr-shot__light" src="../../assets/images/screenshots/policies-list-light.png"
       alt="Policies list with the New policy button highlighted in the top right.">
  <img class="nr-shot__dark" src="../../assets/images/screenshots/policies-list-dark.png"
       alt="Policies list with the New policy button highlighted in the top right.">
  <figcaption class="nr-shot__caption">Governance · Policies · New policy</figcaption>
</figure>

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
[Human approval](human-approval.md)). The two are separate rule
objects; ToolBlock and approval rules don't share a configuration
schema.

ToolBlock is **always Hard**: it never lets through, regardless of
the budget's `enforcement_mode`. See
[Reliability matrix](../concepts/circuit-breaker.md#when-the-gateway-is-unreachable).
If the gate cannot evaluate the ToolBlock check (Redis or policy
cache unavailable), it fails closed — `403 TOOL_BLOCKED` (SDK
`error_code = "NR-T001"`). The agent never runs an unverified
sensitive operation.

ToolBlock and approval rules are distinct rule objects — they don't
share a configuration schema. A ToolBlock policy always *blocks*; to
require human review first, use an approval rule instead.

## A worked example

Suppose your agent has these tools: `tavily_search`, `send_email`,
`db.write`, `db.drop`, `stripe.charge`, `read_file`.

You want to:

- Allow read-only operations (`tavily_search`, `read_file`)
- Block destructive operations (`db.drop`, `stripe.charge`)
- Require approval for any outbound communication (`send_email`)
- Allow normal DB writes (`db.write`) but block `db.drop`

Two ToolBlock policies and one approval rule:

!!! info "The example below shows the request payload shape — what you POST to the dashboard / API. It's not the storage schema, just the public input format."

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

**Approval rules** (separate from ToolBlock) are gated by the
`approvals` plan feature. The per-tier cap matches:

| Plan | Approval rules allowed | Why |
|---|---|---|
| Lite | 0 | `approvals` feature disabled |
| Starter | 0 | `approvals` feature disabled (server-side invariant: `approval_rules > 0 ⇒ approvals == true`) |
| Growth | 20 | `approvals` enabled |
| Scale | unlimited | `approvals` enabled, no cap |
| Enterprise | unlimited | `approvals` enabled, no cap |

The gate enforces `approval_rules = 0` server-side on Lite and
Starter — even if you mint a key on a higher tier and downgrade,
existing rules are kept (for audit) but no new rule can be created
until the plan is upgraded back.

On Lite / Starter, the dashboard shows ToolBlock policy creation
greyed out with an "Upgrade" link.

## How to debug a block you didn't expect

If your agent reports `error_code = "NR-T001"` (wire `TOOL_BLOCKED`) on
a call you think should be allowed:

1. Open the workflow in the dashboard.
2. Click **Effective policy**. The merged set shows every ToolBlock
   pattern that could match.
3. Open the **Audit log** and filter by `decision = block` and
   the tool name. The log shows which pattern matched.
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

## Deep dive

!!! info "Deep dive"

    ToolBlock policies flow through `check_tool_block`
    (`backend/src/proxy/http/gate/orchestrator.rs`), which resolves
    the canonical tool list as `effective_tools = req.tools ++
    req.tool` (TB-1/TB-2/TB-3/TB-4 fail-CLOSED trajectory) — singular
    `tool` is treated as the primary tool when `tools` is absent or
    empty. The helper looks up the per-key `KeyPolicy.tool_patterns`
    (set by the aggregator at `aggregate_policies` walking the
    canonical `tool_pattern` / `blocked_tools` / `tools` keys) and
    runs `glob_match` for every entry. `glob_match_single` handles
    single-`*` patterns; `glob_match_multi` splits on every `*` and
    requires each non-empty literal segment to appear in order
    (v3.39 / DEF-POLFLOW-TB-06). On match, the orchestrator returns
    `Block { TOOL_BLOCKED }` with `details.matched_pattern` so the
    audit log records exactly which pattern fired; the bridge at
    `alert/bridges.rs::dispatch_policy_violation_alert` spawns a
    detached task so a missing db handle never blocks the gate
    response. The tool name validation at `validate_tool_name`
    rejects control / newline bytes on BOTH the singular `tool` and
    every entry of `tools[]` (DEF-SDKT-002) BEFORE the policy check
    runs.

    ToolBlock is ALWAYS Hard, regardless of `enforcement_mode`
    (CLAUDE.md §8). The orchestrator's Step 3 runs before the budget
    reserve, so a blocked tool never gets a budget envelope minted
    — the agent never runs an unverified sensitive operation.
    Pattern length is capped at **4096 bytes per entry**
    (`MAX_POLICY_PATTERN_BYTES`,
    `backend/src/proxy/http/validation.rs`); the cap exists because
    the matcher scans every pattern on every gate call. The
    validator rejects four fail-OPEN traps at policy creation:
    `tool_pattern: ""` (DEF-POLBIZ-06-02), `tool_pattern: []`
    (DEF-POLBIZ-06-01), `config: {}` (DEF-POLBIZ-06-03), and the
    PLURAL `tool_patterns` key (DEF-COMBOFLOW-TB-01, closure
    2026-08-10). The canonical key set is exactly
    `{tool_pattern, blocked_tools, tools}` — any other key (typo like
    `block_tools`, `tools_block`, `blocked_tool`) is rejected with a
    `BadFormat` error (DEF-TS99-001, 2026-09-16), and the matcher is
    case-insensitive against the canonical tool name (CLAUDE.md §8).

    Glob variants: `*` alone matches everything; `bash.*`
    smart-matches `bash` AND `bash.foo` / `bash.foo.bar` (templates
    ship this shape); `send_*` matches anything starting with
    `send_`; `*.drop_*` matches `s3.drop_table` because the
    multi-`*` matcher takes literal segments in order. Alternation
    via `|` (`bash|sh|shell` collapses three patterns into one entry
    in `orchestrator.rs`); no `**`, no `?`, no character classes —
    those are rejected as literals. The aggregator HashSet-dedups
    trimmed entries (TB-H2 closure, 2026-08-12) so `"bash"` and
    `"bash "` (trailing space) collapse to one — purely a cache-bloat
    fix, no semantic change. `check_tool_block` runs inside
    `run_gate_orchestrator` Step 3, BEFORE Step 5 rate-limit and
    Step 9 budget reserve; a blocked tool never reaches the Lua
    `RESERVE` call.

    Two designs were rejected. (1) **Pre-TB-1 fail-OPEN on missing
    `tools`** — pre-fix, an SDK omitting the `tools` field while the
    key had active `tool_patterns` slipped past `check_tool_block`
    and proceeded to the budget reserve; the fix made the
    absent-`tools` path fail-CLOSED whenever `tool_patterns` is
    non-empty. (2) **Globbing the JSON config's argument bag** — the
    matcher operates on the canonical tool name only
    (`glob_match_does_not_look_at_tool_arguments`,
    `orchestrator.rs`); operators do NOT write JSONPath rules over
    tool payloads (CLAUDE.md §"What is NOT stored"). Per-policy
    `action = require_approval` was rejected because the two rule
    types have distinct config shapes; a ToolBlock policy never
    produces `require_approval`. The 4096-byte cap was chosen
    because a 10 MB pattern would burn CPU on every gate call —
    4096 is the longest real-world pattern observed in templates +
    operator overrides.

    `ToolBlock` policies are gated to **Growth+** plans (Lite /
    Starter cannot create them; the dashboard greys out creation
    with an "Upgrade" link), and approval rules are a SEPARATE
    feature gated by `approvals` (Growth: 20, Scale / Enterprise:
    unlimited); the gate enforces `approval_rules = 0` server-side
    on Lite / Starter. The matcher ignores whitespace inside
    patterns (the LLM-facing tool name is stripped by the SDK before
    `/check`), so operators who need to match a tool with whitespace
    in its name must use a wildcard pattern instead of a literal.
    The `*` pattern alone blocks EVERYTHING — narrowing is the
    operator's responsibility; the "Effective policy" tab surfaces
    the merged set so a misconfigured `*` is visible before it
    ships. The validator's 4096-byte cap is per entry, so operators
    that need longer patterns must split across multiple entries
    (HashSet-dedup guarantees no duplicate enforcement).
