---
title: Decorators & context managers
maturity: stable
description: Reference for @protect (the gate decorator) and the workflow / span / chain / attempt context managers it pairs with, plus the with nullrun.guard(): friendly-exit wrapper.
---

# Decorators & context managers

This page is the deep-dive reference for the SDK's runtime-API
surface — every decorator and context manager that affects **how a
function call enters the gate**. The top-level symbol table is in
[SDK API](sdk-api.md); this page explains the *contracts* each
symbol establishes with the gate.

`@protect` is the universal gate decorator. Every protected function
call goes through the four pre-execution gates (control plane /
budget / span / per-tool policy) and emits a tool-call span event
tagged with the masked arguments. Wrap the call site in
`with nullrun.guard():` for the structured 4-line developer report
on failure.

## The canonical API: `@protect` only

`@protect` is the single canonical public entry point for the SDK.
It is the gate. Every protected function call goes through the four
pre-execution gates (control plane / budget / span / per-tool
policy) and emits a tool-call span event tagged with the masked
arguments.

The split is intentional: the SDK collects facts (`tool_name`,
`args`, `kwargs`) and ships them on the wire; the backend decides
what to do with them. Business semantics — "this is a money tool",
"this requires human approval" — live in NullRun policies, not in
another decorator on the function. See
[Human approval](../concepts/human-approval.md) for how operators
configure the typed predicates the gate evaluates.

## What's in scope

| Symbol | Type | Surface |
|---|---|---|
| `@protect` | decorator | eager (`from nullrun import protect`) — **canonical** |
| `with guard():` | context manager | eager (`from nullrun import guard`) |
| `with workflow(...)` | context manager | lazy (`from nullrun import workflow`) |
| `with span(...)` | context manager | lazy |
| `with agent(...)` | context manager | lazy |
| `with attempt(...)` | context manager | lazy |
| `with chain(...)` | context manager | lazy |
| `set_call_context(...)` | imperative setter | lazy |

Setters that only enrich observability
(`set_trace_id`, `set_operation_id`, …) are not covered here —
they are internal hooks the runtime drives from inside `@protect`.

---

## `@protect` — the gate decorator

**Parameters: none.** `@protect` accepts only a callable (or `None`
when written with empty parens — the standard
`@decorator` ↔ `@decorator()` shape).

```python title="protect_basic.py"
@nullrun.protect
def my_agent(prompt: str) -> str:
    return call_llm(prompt)

@nullrun.protect
async def my_async_agent(prompt: str) -> str:
    return await call_llm_async(prompt)

@nullrun.protect()      # also valid — `fn=None` returns the decorator itself
def f(): ...
```

### What `@protect` does on every call

A single `@protect` call runs **four pre-execution gates** in
strict order (ADR-008 Rule 4). The wrapper is shared between the
sync and async paths via a `_protect_body` context manager; only
the kill/pause signal translation differs.

| # | Gate | Failure mode | Sync behaviour | Async behaviour |
|---|---|---|---|---|
| 1 | `check_control_plane(workflow_id)` — KILL/PAUSE from the dashboard | **fail-CLOSED** (kill is terminal) | Raise `NullRunBlockedException(NR-W002)` / `(NR-W003)` | Re-raise the underlying `NullRunWorkflowKilledError` unchanged |
| 2 | `check_workflow_budget()` — `/gate` pre-flight reservation | **fail-OPEN** on transport error (a transient backend outage must not freeze the user's agent) | `NullRunBudgetError(NR-B004)` on real block; transport error logs and proceeds | identical |
| 3 | `_emit_span_start(...)` — observability `span_start` event | **never blocks** — exceptions swallowed at DEBUG | identical | identical |
| 4 | `_run_tool_policy_gate(...)` — `/execute` per-tool policy | **fail-CLOSED** on transport error (a denied `charge_card` that runs when the policy engine is down is worse than a denied `charge_card` during an outage). Opt out via `NULLRUN_SENSITIVE_FAIL_OPEN=1`. | `NullRunBlockedException` on real block; on `NullRunTransportError` re-raises with source-specific `error_code` (NR-B001/NR-B002/NR-A003/NR-B005) | identical |

After the body completes, `@protect` calls
`runtime.track_tool(fn.__name__, metadata={"arguments": _safe_kwargs(kwargs)})`
to emit a tool-call span event tagged with the masked arguments.
Sensitive kwargs (PANs, tokens, etc., per `SENSITIVE_ARG_KEYS`)
are replaced with `"***"` **before** truncation so a long URL
never escapes the redaction window.

If any gate raises and the function body never ran, the wrapper
calls `_safe_cancel_active_execution(reason="tool_exception")` —
this hits `POST /cancel` to close the open Redis reservation
that `/gate` minted, so the budget doesn't leak via TTL expiry.

### Wire payload on `/execute`

Every `@protect` call ships a `NoImpact` envelope — the SDK is
policy-blind and the backend owns the decision.

| Field | Value | Source |
|---|---|---|
| `tool_name` | `fn.__name__` | the decorated function |
| `input_data` | `{"args": masked_args, "kwargs": masked}` | positional and keyword arguments, PII-masked |
| `business_impact` | `None` | wire-shape compat — backend reads only `action_digest` + `kwargs` |
| `action_digest` | SHA-256 hex (64 chars) of `BusinessImpact.no_impact()` | `compute_action_digest(...)` |
| `tools` | tuple of tool names (defaults to `(fn.__name__,)` if unset) | `set_call_context(tools=...)` or the `@protect` default |

### Sync vs async: the kill-signal divergence

The sync wrapper passes `unify_block=True` so a kill arriving
during `@protect`'s own scaffolding is rewrapped into a single
`NullRunBlockedException` the user can catch uniformly. The async
wrapper passes `unify_block=False` — async frameworks
(`asyncio.CancelledError`, signal handlers) rely on the original
typed exception to interrupt cleanly. Re-raising
`NullRunWorkflowKilledError` as-is is required, not a bug.

### Span hierarchy (built automatically)

`_next_span()` reads `get_current_span()`. If a parent span is
already active (outer `@protect`, `with workflow`, `with span`),
the new span becomes a child. Otherwise a fresh root is opened.

```python title="protect_span_tree.py"
@nullrun.protect
def orchestrator(q):
    return researcher(q)             # child span

@nullrun.protect
def researcher(q):
    return get_current_span()        # parent.span_id == its parent_span_id
```

The dashboard reconstructs the whole tree from the
`parent_span_id` chain emitted in `span_start` events. You do not
need to pass span context through arguments.

### When to use

**Always** on any function that calls an LLM, makes a tool call,
or spends money. `@protect` is the gate. The workflow is derived
from the API key on the backend; `fn.__name__` becomes the
`tool_name` for the policy engine.

---

## `with nullrun.guard():` — friendly-exit wrapper

The **canonical form is `with nullrun.guard():`** — it makes the
scope explicit and prints the structured four-line developer report
on any `NullRunError`.

**Parameters: none.** `guard()` accepts an optional `exit_code=`
keyword (default `1`).

```python title="guard_canonical.py"
import nullrun
from nullrun import protect

@protect
def my_agent(prompt: str) -> str:
    return call_llm(prompt)


if __name__ == "__main__":
    with nullrun.guard():
        print(my_agent("hello"))
```

### What it does

Any `NullRunError` raised inside the `guard()` block is caught,
rendered as the **structured four-line developer report**
(`[error_code]` + `what` + `where` + `why` + `how to fix`), printed
to **stderr**, and the process exits with code `1`.

The catalog user-message is the headline line so end-user-facing
deployments still get a clean single sentence; the structured detail
below it is the developer-facing fix.

Exceptions that propagate unchanged:

- `NullRunWorkflowKilledError` (kill signal) — kill must reach the
  top of the agent loop, not be swallowed into a graceful exit.
  Re-raised explicitly inside the `except NullRunError` branch.
- `KeyboardInterrupt` / `SystemExit` — same reason; they don't reach
  the `except NullRunError` branch anyway.
- Any non-NullRun exception — the user's own bugs are not handled
  here; let them propagate for an honest traceback.

### When to use

For **top-level entry points** in scripts and CLIs: instead of a
raw traceback on `NullRunConfigError(NR-C001)` at the first gate
call, the operator sees the structured four-line developer report
and the process exits cleanly. In libraries and long-running
services, prefer `try/except NullRunError` — `guard()` exits the
process, which isn't appropriate there.

The context-manager form `with nullrun.guard():` is the
**recommended form** for region-of-code scopes — see the example
above. It makes the scope explicit, accepts an `exit_code=` argument,
and the four-line report is what it always renders. If `run_my_agent`
raises `NullRunError` inside the block, the four-line developer
report is printed (catalog headline + error_code + what + where +
why + how to fix) and the script exits 1.

### Zero-activity diagnostic

The runtime tracks `_protect_call_count` and
`_llm_call_event_count`. If `@protect` fires 50+ times without the
runtime observing a single `track_llm` event — typically a sign
that auto-instrumentation did not attach (vendor SDK imported
later, custom transport not on httpx, framework hook missing) —
the SDK logs **one** WARNING naming the three most likely root
causes. The diagnostic is warn-once; subsequent bumps do not spam.

---

## Context managers

| Context manager | Parameters | What it sets |
|---|---|---|
| `with workflow(name=None)` | `name: str \| None` | Root scope: pushes `workflow_id` + `trace_id` + `span_id` (root `SpanContext`). All `@protect` and `track_*` calls inside auto-tag events with this `workflow_id`. |
| `with span(name=None)` | `name: str \| None` | Child span derived from the active parent `SpanContext`. No-op if no parent is active (bare `with span(...)` outside any workflow/protect block). |
| `with agent(name=None)` | `name: str \| None` | Sets `agent_id` for per-agent cost attribution. |
| `with attempt(attempt_index)` | `attempt_index: int` | Sets `attempt_index` for retry correlation. |
| `with chain(chain_id, op="start")` | `chain_id: str` (UUID v4), `op: str` | Soft-mode budget gate. Overdrafts are allowed only when an active chain is registered against the org. `op` is `"start"` / `"continue"` / `"end"` / `"auto"` (default). |

### `workflow()` and the policy binding

The `workflow_id` is the join key that binds a run to a
dashboard-defined workflow (with its budget cap and per-workflow
policies). The name you pass should match the workflow your API
key is bound to — otherwise the gate falls back to an ad-hoc
workflow_id with no budget policy attached. For a one-shot test
script, `None` is fine: the SDK mints a UUID and the run lives as
an unattached workflow.

### `chain()` and the UUID v4 validation

```python title="chain_uuid.py"
import uuid
import nullrun

chain_id = str(uuid.uuid4())       # MUST be a UUID v4 string
with nullrun.chain(chain_id, op="start"):
    my_long_running_agent()        # every /gate call extends the chain TTL
```

The `chain_id` is validated client-side per CLAUDE.md §6: the
backend's chain race guard (`HGET chain_key 'org_id'`) does **not**
validate UUID format — non-UUID or non-v4 `chain_id`s silently
auto-register as new ACTIVE chains, which is both a typo trap
and a predictable-UUID risk. The SDK raises `ValueError` at
`with chain(...)` entry on malformed input.

`chain` is the soft-mode companion to a Hard budget: the budget
allows a bounded overrun only when an active chain is present.
Long-running streams should also call
`runtime.ping_chain(chain_id, interval=30.0)` to extend the TTL
faster than the natural `/check` cadence.

### Nested `with span(...)`

```python title="nested_span.py"
with nullrun.workflow("my-agent"):
    with nullrun.span("plan-generation"):     # child of workflow root
        plan = my_agent(user_input)
        with nullrun.span("tool-call"):       # grandchild
            tool.invoke(plan)
```

The dashboard renders the tree from the `parent_span_id` chain
emitted in `span_start` events — there is no manual context
threading.

---

## `set_call_context()` — per-call data for `/gate`

```python title="set_call_context.py"
nullrun.set_call_context(
    model="claude-sonnet-4-6",     # LLM model name; backend looks up per-model rate
    tools=["send_email", "refund_customer"],   # matched against workflow's blocked_tools
)
```

| Parameter | Type | Default | Effect when unset |
|---|---|---|---|
| `model` | `str \| None` | `None` (no change) | Backend reads the rate from the workflow default; per-model budget tiers do not fire. |
| `tools` | `list[str] \| tuple[str, ...] \| None` | `None` (no change) | Backend skips `ToolBlock` enforcement on `/gate`. Pass `[]` to clear (different from `None`, which leaves the previous value). |

Call this **inside** a `with workflow(...)` block, before the
`@protect` call. The values are forwarded on the `/gate` request
so the backend can:

- compute `projected_cost` from the **real** model rate (not the
  default fallback);
- evaluate the workflow's `blocked_tools` aggregate against the
  call's intended tool list (otherwise `ToolBlock` only runs on
  `/track`).

Both fields default to `None` / empty; users opt in by calling
`set_call_context` explicitly. The `@protect` wrapper itself
populates the `tools` field with `(fn.__name__,)` if the user
didn't — a defensive default so a bare `@protect` still triggers
the tool-block check for that single function name.

---

## How ToolParameters approval rules work

The `@protect` envelope ships `tool_name + args + kwargs` plus a
`NoImpact` envelope (kind=`"none"`) on every call. Approval rules
that need to inspect argument values reference them by `param_name`
in the dashboard approval-rule editor — the backend reads the live
value out of `kwargs` directly. There is no SDK-side extractor and
no decorator to configure; the wire payload carries everything the
rule needs.

The canonical envelope (`BusinessImpact.no_impact()`) computes to
the same 64-char SHA-256 `action_digest` on every call. The digest
binds approval grants to the exact payload — backend
re-checks the digest on `/execute` and refuses on mismatch.

---

## When to use what

| Task | API |
|---|---|
| Wrap a function that calls an LLM or tool (canonical) | `@nullrun.protect` (no parameters) |
| Mark a money-moving tool for typed approval + digest | `@nullrun.protect` + an approval rule referencing `param_name` in the dashboard |
| Mark a tool where rule names ≠ arg names | Approval rule `param_name` mapping in the dashboard |
| Top-level script entry (friendly exit) | `with nullrun.guard():` |
| Multi-step agent run (cost + trace per workflow) | `with nullrun.workflow("agent-name"): ...` |
| Per-call model name and tools for `/gate` | `nullrun.set_call_context(model=..., tools=[...])` inside `with workflow` |
| Soft-mode budget (controlled overdrafts) | `with nullrun.chain(uuid.uuid4(), op="start"): ...` |
| LangGraph auto-tracking | (auto on first `@protect` call) |
| Manual LLM tracking (custom client) | `nullrun.track_llm(input_tokens=..., output_tokens=..., model=...)` |
| Manual tool-call tracking | `nullrun.track_tool(tool_name=..., duration_ms=..., metadata=...)` |
| Custom business event | `nullrun.track({"type": "agent.milestone", "step": ..., "elapsed_secs": ...})` |
| Audit log read | `runtime.audit.list(AuditQuery(event_type=..., since=..., limit=...))` |
| Global error hook (Sentry, OTel) | `nullrun.on_error(my_handler)` — returns an idempotent unregister callable |
| Snapshot runtime state | `nullrun.get_runtime().status()` — frozen `NullRunStatus` dataclass |
| Graceful exit (WS close, flush events) | `nullrun.shutdown()` — auto-registered via `atexit` inside `init()`; explicit calls only matter for tests (`shutdown(flush=False)`) or for early teardown |

---

## Order of application — cheat sheet

```python title="order_cheatsheet.py"
# ─── Canonical: just @protect ───
@nullrun.protect
def delete_user(uid: int): ...           # ToolParameters rules "just work"

# ─── Plain trackable function ───
@nullrun.protect
def my_agent(prompt): ...

# ─── Nested @protect builds the span tree automatically ───
@nullrun.protect
def orchestrator(q):
    return researcher(q)              # child span

@nullrun.protect
def researcher(q):
    return get_current_span()         # parent's span_id == parent_span_id

# ─── Top-level script entry with friendly exit (guard() preferred) ───
import nullrun
from nullrun import protect

@protect
def main(prompt): ...

if __name__ == "__main__":
    with nullrun.guard():               # canonical — 4-line report + exit 1
        print(main("hello"))
# shutdown() is auto-registered via atexit inside init() —
# no explicit call is needed for a clean WS close on exit.

# ─── Full layering: chain → workflow → call context → @protect ───
# The runtime is created lazily on the first @protect call.
# NULLRUN_API_KEY must be set in the shell.
import uuid
import nullrun

chain_id = str(uuid.uuid4())
with nullrun.chain(chain_id, op="start"):           # soft-mode budget
    with nullrun.workflow("customer-support"):        # root trace
        with nullrun.span("plan-generation"):        # child span
            nullrun.set_call_context(                # model + tools for /gate
                model="claude-sonnet-4-6",
                tools=["send_email", "refund_customer"],
            )
            plan = my_agent(user_input)              # @protect inside
```

---

## Anti-patterns

!!! warning "Don't put `with nullrun.guard():` inside a `@protect`-wrapped body"
    `guard()` only catches errors raised inside its own block. A
    bare `with nullrun.guard():` placed inside a `@protect`-decorated
    function is a no-op for gate-time errors — the exception is
    raised by the `@protect` wrapper before the body runs, never
    reaches the `with` block, and the process exits with a raw
    traceback instead of the four-line developer report.

!!! warning "Don't pass `cost_cents` to `track_llm`"
    The SDK strips it before sending. Cost is recomputed on the
    backend from `input_tokens + output_tokens + org pricing policy`.
    `tokens` is the only valid unit on the wire.

!!! warning "Don't call `set_chain_id("my-custom-id")`"
    `chain_id` MUST be a UUID v4 string per CLAUDE.md §6. The
    backend's race guard does not validate format — non-v4 ids
    silently auto-register as new ACTIVE chains. Use
    `with nullrun.chain(uuid.uuid4(), op="start")` to let the SDK
    validate.

!!! danger "Don't use `set_call_context(model="...")` to override cost"
    `model` only changes which rate the backend uses to compute
    `projected_cost`. The actual cost comes from real token counts
    on `/track`. Faking `model` to lower the projected cost doesn't
    reduce the actual charge.

---

## See also

- [SDK API](sdk-api.md) — top-level symbol table, exceptions, manual
  tracking, transport hooks
- [Sensitive tools (concept)](../concepts/sensitive-tools.md) —
  `ToolBlock` server-side policy and how `@protect` interacts with it
- [Human approval](../concepts/human-approval.md) — typed predicates
  (`money_amount`, `tool_parameters`) and `action_digest`
- [Workflows](../concepts/workflow.md) — dashboard-side view of a
  workflow (budget cap, API keys, executions, traces)
- [Custom tracking](../how-to/custom-tracking.md) — when to use
  `track_llm` / `track_tool` / `track` instead of
  auto-instrumentation
- [Use with LangGraph](../how-to/langgraph.md) — LangGraph auto-patch
  and how `@protect` instruments a graph
