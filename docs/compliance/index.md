---
title: Compliance
maturity: stable
description: NullRun's compliance posture — what data crosses the wire, what is stored, who can reach it, and what happens when it is deleted.
---

# Compliance

NullRun sits between an agent and the tools it calls, so it sees the
tool payloads it decides on. This section documents that view: what
data crosses the wire, what is persisted, who can reach it, and what
happens when it is deleted.

| Page | Purpose |
| --- | --- |
| [Data handling & vendor review](data-handling.md) | The full inventory — what is transmitted, what is stored, retention, sub-processors, and the answers to a standard vendor risk questionnaire. |

!!! info "What NullRun does and does not inspect"

    The gate is a **decision** layer, not a content scanner. It
    evaluates structured metadata about a call — tool name, model,
    declared sensitivity, cost, scope — and returns `allow`,
    `soft_pass`, `require_approval`, `block`, or `deny` before the call
    executes. `soft_pass` lets the call run and books the overspend as
    an overdraft.

    It does not read the free-text arguments of a tool call to decide
    whether the *content* is acceptable. A payload that passes the
    gate because its metadata looked benign is not scanned
    afterwards. Enforce content-level inspection in the agent,
    upstream of NullRun.

    The inverse also holds: the gate never needs a call to have
    completed in order to block it. A decision is returned before
    execution begins, so a blocked call costs nothing and leaves no
    side effect behind.

## See also

- [Data handling & vendor review](data-handling.md) — the full
  inventory
- [Performance & limits](../operations/performance.md) — timeouts and
  the fail-closed posture
- [API keys](../concepts/api-keys.md) — signing, rotation, revocation
