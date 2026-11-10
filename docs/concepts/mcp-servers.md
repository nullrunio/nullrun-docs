---
title: MCP servers
maturity: stable
description: MCP servers as a source of tools — how a call is named, how the operator decides which tools run, and what the SDK raises when the gate refuses.
---

# MCP servers

An **MCP server** is a source of tools for your agent. The agent
discovers the server's tools, and each call is evaluated by the gate
like any other tool call.

## How a tool is named

The canonical name of an MCP tool carries the server it came from:

```
mcp://{server}/{tool}
```

| Example | Server | Tool |
|---|---|---|
| `mcp://github/create_issue` | `github` | `create_issue` |
| `mcp://filesystem/read_file` | `filesystem` | `read_file` |

The server name is the first segment. The rest is the tool name, and it
may contain slashes.

The SDK does not build that name. `MCPAdapter.call_tool("create_issue", …)`
sends the bare tool name, and the gateway resolves it against your
organization's own catalog. Every server that declares that tool takes
part, and the strictest decision wins. A tool no server declares stays a
plain tool name.

Policy patterns are written against the canonical name. See
[Tool policies → What a tool name looks like](tool-policies.md#what-a-tool-name-looks-like).

## Deciding which tools run

The **Action sources** page in the control center lists the servers your
agents call and the tools they expose. Each tool carries one decision:

| Decision | What it means |
|---|---|
| **Allow** | The tool runs. |
| **Ask** | The tool is refused. The control center labels it "Behaves as block today". |
| **Block** | The tool is refused. |

A tool with no decision is refused. The operator has to choose.

The gate also compares the tool's current definition with the definition
the operator accepted. A changed definition is refused even when the
decision is **Allow**, and a tool the server has dropped is refused too.
The drift check runs before the decision, so a tool the operator allowed
and never re-accepted is refused first. Accepting the new definition does
not allow the tool — the operator still has to set the decision to
**Allow**.

## Refusals

The gate refuses an MCP call with one of these codes:

| Wire code | HTTP | SDK class | Meaning |
|---|---|---|---|
| `MCP_TOOL_BLOCKED` | 403 | `NullRunToolBlockedError` | The decision is block. |
| `MCP_TOOL_REMOVED` | 403 | `NullRunToolBlockedError` | The server no longer offers the tool. |
| `MCP_DEFINITION_DRIFTED` | 403 | `NullRunApprovalToolDigestMismatchError` | The tool's definition changed after the operator accepted it. |
| `MCP_TOOL_DECISION_REQUIRED` | 403 | `NullRunMcpApprovalRequiredError` | Nobody has chosen a decision for this tool. |
| `MCP_TOOL_APPROVAL_REQUIRED` | 403 | `NullRunMcpApprovalRequiredError` | The decision is ask. |
| `MCP_REGISTRY_UNAVAILABLE` | 503 | `NullRunBackendError` | The registry could not be read. The call is refused and can be retried. |

Two facts about `MCP_TOOL_APPROVAL_REQUIRED` catch people out:

- The wire decision is **block**, not `require_approval`. There is no
  approval row and no approval id. The refusal never reaches a human.
- The call succeeds once the operator changes the decision on the catalog
  row to **Allow**. There is no per-call approval round trip for an MCP
  tool.

Three MCP-specific codes exist in the SDK:

| SDK code | SDK class | Meaning |
|---|---|---|
| `NR-MCP01` | `NullRunMcpDestructiveBlockedError` | A destructive tool was blocked. |
| `NR-MCP02` | `NullRunMcpReadonlyBypassBlockedError` | A read-only bypass was blocked. |
| `NR-MCP03` | `NullRunMcpApprovalRequiredError` | The call needs an operator decision. |

`NR-MCP01` and `NR-MCP02` belong to the MCP umbrella policies. The gate
evaluates the per-tool decision instead, and the gate does not read the
umbrella policies. The two codes stay reserved so an SDK can tell the
refusal families apart.

`NR-MCP03` is what the SDK raises when the gate refuses with
`MCP_TOOL_APPROVAL_REQUIRED` or `MCP_TOOL_DECISION_REQUIRED`. It carries
`retryable = True`, because the operator can still decide.

## Calling an MCP tool from the SDK

`MCPAdapter` is the helper that gates MCP calls. It wraps a connected
MCP client, discovers the server's tools, and routes every call through
the gate before the client runs.

```python
import nullrun
from nullrun.toolbox.mcp import MCPAdapter

nullrun.init(api_key="nr_live_...")

# Your own MCP client — the adapter does not open the connection.
client = your_mcp_client_library.connect(url="https://your-mcp-server")

adapter = MCPAdapter(server_name="github", mcp_client=client)

result = adapter.call_tool(
    "create_issue",
    {"repo": "acme/api", "title": "Crash on checkout"},
)
```

What the adapter does on every call:

- Routes the call through the gate first. A refused call raises
  `NullRunBlockedException` and the MCP client is not invoked.
- Reads the server's tool list and forwards the tool's annotations to the
  gate. The `readOnlyHint`, `destructiveHint`, and `openWorldHint` hints
  become the gate's read-only, destructive, and open-world flags.
- Derives the action digest from the tool name and the exact argument bag
  it forwards, so an operator approval binds to that payload.

Two constructor options matter:

| Option | Effect |
|---|---|
| `cache_seconds` | How long the tool list is cached. Must be `0` or at least `30`. `0` re-reads the tool list on every call. |
| `runtime` | The runtime to gate through. Pass one to use a specific runtime; leave it unset to use the global one. |

When the tool list cannot be read, the adapter tells the gate that the
annotations are unknown. It never presents a stale hint as the server's
current answer.

## Getting an MCP tool approved

The registry decision and an approval rule are two different mechanisms.

The registry's **Ask** decision refuses the call and creates no approval
row. The operator changes the decision on the catalog row to **Allow**,
and the next call runs.

An [approval rule](human-approval.md) is the mechanism that parks a call
for a human. When a rule matches, the gate returns `require_approval`,
and the adapter re-enters with the grant:

```python
from nullrun import NullRunError

try:
    result = adapter.call_tool(
        "create_issue",
        {"repo": "acme/api"},
        approval_id=approval_id,
    )
except NullRunError as exc:
    # exc.error_code tells you which refusal you got.
    raise
```

The adapter derives the digest and the impact envelope from the tool name
and the argument bag, so the grant binds to those exact arguments. The
wire contract for the approval is in
[Human approval](human-approval.md).

## See also

- [Tool policies](tool-policies.md) — the tool-name format and matching rules
- [Human approval](human-approval.md) — writing an approval rule for one tool
- [Sensitive tools](sensitive-tools.md) — starter patterns for destructive tools
