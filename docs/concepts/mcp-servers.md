---
title: MCP servers
maturity: stable
description: MCP servers as a source of tools — how their tools are named, how the operator decides which ones run, and how the SDK gates a call.
---

# MCP servers

An **MCP server** is a source of tools for your agent. The agent discovers the server's tools, and each call is evaluated by the gate like any other tool call.

## Tool names

An MCP tool has a canonical name that carries the server it came from:

```
mcp://{server}/{tool}
```

| Example | Server | Tool |
|---|---|---|
| `mcp://github/create_issue` | `github` | `create_issue` |
| `mcp://filesystem/read_file` | `filesystem` | `read_file` |

The server name is the first segment. The rest is the tool name, and it may contain slashes.

These names work everywhere a tool name works. A [tool policy](tool-policies.md) pattern can match them, and an [approval rule](human-approval.md) can require review for one. See [Tool policies](tool-policies.md#what-a-tool-name-looks-like) for the full name format.

## Deciding which tools run

The **MCP servers** page in the dashboard lists the servers your agents call and the tools they expose. Each tool carries one decision:

| Decision | What it means |
|---|---|
| **allow** | The tool runs. |
| **ask** | The tool does not run until an operator approves it. |
| **block** | The tool never runs. |

A tool with no decision does not run. The operator has to choose.

The gate also compares the tool's current definition with the definition that was approved. A changed definition is refused even when the decision is **allow**, and a tool the server has dropped is refused too.

## Refusals

The gate refuses an MCP call with one of these codes:

| Wire code | SDK class | Meaning |
|---|---|---|
| `MCP_TOOL_BLOCKED` | `NullRunToolBlockedError` | The operator set the decision to block. |
| `MCP_TOOL_REMOVED` | `NullRunToolBlockedError` | The server no longer offers the tool. |
| `MCP_TOOL_APPROVAL_REQUIRED` | `NullRunMcpApprovalRequiredError` | The decision is ask and no operator has approved the call. |
| `MCP_TOOL_DECISION_REQUIRED` | `NullRunMcpApprovalRequiredError` | The operator has not chosen a decision for this tool. |
| `MCP_DEFINITION_DRIFTED` | `NullRunApprovalToolDigestMismatchError` | The tool's definition changed after the operator approved it. |
| `MCP_REGISTRY_UNAVAILABLE` | `NullRunBackendError` | The registry could not be read. The call is refused and can be retried. |

Three MCP-specific codes exist in the SDK:

| SDK code | SDK class | Meaning |
|---|---|---|
| `NR-MCP01` | `NullRunMcpDestructiveBlockedError` | A destructive tool was blocked. |
| `NR-MCP02` | `NullRunMcpReadonlyBypassBlockedError` | A read-only bypass was blocked. |
| `NR-MCP03` | `NullRunMcpApprovalRequiredError` | The call needs an operator approval. |

`NR-MCP01` and `NR-MCP02` belong to the MCP umbrella policies. The gate evaluates the per-tool decision instead, and the gate does not read the umbrella policies. The two codes stay reserved so an SDK can tell the refusal families apart.

`NR-MCP03` is what the SDK raises when the gate refuses with `MCP_TOOL_APPROVAL_REQUIRED` or `MCP_TOOL_DECISION_REQUIRED`.

## Calling an MCP tool from the SDK

`MCPAdapter` is the helper that gates MCP calls. It wraps a connected MCP client, discovers the server's tools, and routes every call through the gate before the client runs.

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

- Checks the call against the gate. A blocked call raises `NullRunBlockedException` and the MCP client is not invoked.
- Reads the server's tool list and forwards the tool's annotations to the gate. The `readOnlyHint`, `destructiveHint`, and `openWorldHint` hints become the gate's read-only, destructive, and open-world flags.
- Derives the action digest from the tool name and the exact argument bag it forwards, so an operator approval binds to that payload.

Two constructor options matter:

| Option | Effect |
|---|---|
| `cache_seconds` | How long the tool list is cached. Must be `0` or at least `30`. `0` re-reads the tool list on every call. |
| `runtime` | The runtime to gate through. Pass one to use a specific runtime; leave it unset to use the global one. |

When the tool list cannot be read, the adapter tells the gate that the annotations are unknown. It never presents a stale hint as the server's current answer.

## Approving an MCP call

When the gate needs an approval, the call raises `NullRunMcpApprovalRequiredError`. Its `error_code` is `NR-MCP03`, and the refusal is retryable: the same call succeeds once the operator decides.

```python
from nullrun import NullRunMcpApprovalRequiredError

try:
    adapter.call_tool("create_issue", {"repo": "acme/api"})
except NullRunMcpApprovalRequiredError as exc:
    # Wait for the operator's decision, then call again.
    approval_id = exc.details.get("approval_id")
    ...
```

The wire contract for the approval is in [Human approval](human-approval.md).

## See also

- [Tool policies](tool-policies.md) — the tool-name format and matching rules
- [Human approval](human-approval.md) — writing an approval rule for one tool
- [Sensitive tools](sensitive-tools.md) — starter patterns for destructive tools
