---
title: Index
description: NullRun's compliance posture — what data is transmitted and stored, who can access it, and how it is deleted.
---

# Compliance

NullRun sits between an agent and the tools it calls, so it sees the
tool payloads it decides on. This section documents that view: what
data crosses the wire, what is persisted, who can reach it, and what
happens when it is deleted.

| Page | Purpose | Reference |
| --- | --- | --- |
| Data handling & vendor review | The full data inventory — what is transmitted, what is stored, retention windows, sub-processors, and vendor review. | [Data handling & vendor review](data-handling.md) |

!!! info "What NullRun does and does not inspect"

    The gate is a **decision** layer, not a content scanner. It
    evaluates structured metadata about a call — tool name, model,
    declared sensitivity, cost, scope — and returns `allow`, `block`,
    or `require_approval` before the call executes.

    It does not read the free-text arguments of a tool call to decide
    whether the *content* is acceptable. A payload that slips past the
    gate because its metadata looked benign is not retroactively
    scanned. If you need content-level inspection, enforce it in the
    agent, upstream of NullRun.

    The inverse is also true: the gate never needs the call to have
    completed in order to block it. A decision is returned before
    execution begins, so a blocked call costs nothing and leaves no
    side effect behind.
