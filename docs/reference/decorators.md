---
title: Decorators & context managers
maturity: stable
description: "Reference for @protect — the one gate decorator — and the workflow / span / agent / chain context managers it pairs with, plus the with nullrun.guard(): friendly-exit wrapper."
---

# Decorators & context managers

This page explains the contract each SDK symbol establishes with the
gate. The symbol table lives in [SDK API](sdk-api.md).

`@protect` is the gate. Every protected call is evaluated against
tool patterns, budgets, rate limits, and approval policies before the
function body runs.

## The one decorator

`@protect` is the only public decorator in the SDK. It takes no
arguments.

```python title="protect_basic.py"
import nullrun

@nullrun.protect
def my_agent(prompt: str) -> str:
    return call_llm(prompt)

@nullrun.protect
async def my_async_agent(prompt: str) -> str:
    return await call_llm_async(prompt)

@nullrun.protect()      # also valid
def f(): ...
```

The SDK collects the facts — function name, arguments, keywords — and
ships them on the wire. The gateway decides. Business meaning ("this
moves money", "this needs a human") lives in dashboard policies, not
in a second decorator. See [Human
approval](../concepts/human-approval.md).

### What happens on every call

| # | Step | What it does |
|---|---|---|
| 1 | Control-plane check | Applies a pending **kill** or **pause** before anything else. |
| 2 | Budget pre-flight | Reserves budget for the call. A refusal here stops the call. |
| 3 | Span start | Opens a span for the call. Never blocks. |
| 4 | Tool policy | Evaluates the tool against the org's policies. A refusal here stops the call. |
| 5 | Function body | Runs only if every step above allowed the call. |
| 6 | Tool track | Records the call and its cost. |

Argument names that look like credentials are replaced with `***`
before the call leaves your process. Passwords, tokens, API keys,
authorization headers, session cookies, card numbers, PINs, and OTPs
are covered.

### When the gateway cannot be reached

The SDK distinguishes three outcomes, and they are not the same thing:

| Outcome | What the SDK does |
|---|---|
| The gateway **refused** the call | The refusal is honoured. The call does not run. |
| The gateway is **unreachable** (network error, timeout, 5xx with no refusal body) | The call proceeds. Enforcement is advisory until the gateway recovers. |
| The answer arrived but the SDK **cannot read it** | The SDK raises `NullRunGateIndeterminateError` (`NR-P004`). The call does not run. |

An unanswered question is not a yes. Only the middle row fails open,
and only on the pre-flight step. A credential failure or an
unreadable body raises instead of proceeding.

`NULLRUN_SENSITIVE_FAIL_OPEN=1` exists for local development. On its
own it opens nothing: the set of tools allowed to fail open is empty
until you name the tools explicitly.

```python title="fail_open_tools.py"
runtime = nullrun.get_runtime()
runtime.register_fail_open_tools(["charge_card"])   # local development only
```

### Sync and async differ in one place

A **kill** arriving mid-call is reported differently by the two
wrappers:

| Wrapper | The kill arrives as | The `on_error` hook fires |
|---|---|---|
| sync `@protect` | `NullRunBlockedException` with code `NR-W002` | yes |
| async `@protect` | `WorkflowKilledInterrupt` (code `NR-W002`) | no |

The sync form unifies the signal into one catchable class. The async
form lets the raw interrupt through, so `asyncio` cancellation and
signal handlers behave as they normally do.

Catch the kill by name, ahead of the decision branch:

```python title="catch_kill.py"
try:
    result = run_agent(prompt)
except WorkflowKilledInterrupt:
    raise          # a kill must reach the top of the loop
except NullRunDecision as decision:
    ...
```

### Spans nest automatically

A protected call inside another protected call becomes a child span.
You do not thread span context through arguments.

```python title="protect_span_tree.py"
@nullrun.protect
def orchestrator(q):
    return researcher(q)             # child span

@nullrun.protect
def researcher(q):
    return get_current_span()        # its parent is the orchestrator span
```

## `with nullrun.guard():` — friendly exit

`guard()` turns any `NullRunError` raised inside the block into a
clean message on stderr and a non-zero exit.

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

`guard()` accepts one keyword: `exit_code` (default `1`).

The message is the user-facing sentence first, then the developer
detail — the error code, where it happened, why, and how to fix it.
See [Error handling](../concepts/error-handling.md) for the full
report shape.

These propagate unchanged:

- `WorkflowKilledInterrupt` — the kill must reach the top of the loop.
- `KeyboardInterrupt` and `SystemExit`.
- Any exception that is not a `NullRunError` — your own bugs deserve
  an honest traceback.

Use `guard()` at the entry point of a script or CLI. In a library or
a long-running service, catch `NullRunError` instead — `guard()`
exits the process.

## Context managers

| Context manager | Parameters | What it sets |
|---|---|---|
| `with workflow(name=None)` | `name: str \| None` | The workflow scope. Everything inside is attributed to this workflow. |
| `with span(name=None)` | `name: str \| None` | A child span of the active parent. |
| `with agent(name=None)` | `name: str \| None` | The agent identity, for per-agent cost attribution. |
| `with chain(chain_id, op="start")` | `chain_id: str` (UUID v4), `op: str` | A chain — a group of calls that run as one unit under a shared budget. |

### `workflow()` and the policy binding

The workflow name is what links a run to the budget and policies you
configured in the dashboard. Give it the same name as the workflow
your API key is bound to. If you leave it unset, the SDK generates one
and the run carries no workflow policies.

### `chain()` and the UUID v4 requirement

```python title="chain_uuid.py"
import uuid
import nullrun

chain_id = str(uuid.uuid4())       # must be a UUID v4 string
with nullrun.chain(chain_id, op="start"):
    my_long_running_agent()
```

`op` is one of `start`, `continue`, `end`, `auto`. The default is
`start`.

The `chain_id` is validated when you enter the block. A malformed id
raises `ValueError`. Use `uuid.uuid4()` rather than a readable slug —
the SDK cannot tell a typo from a deliberate identifier.

A chain is the companion to a hard budget: a bounded overrun is
allowed only while a chain is active. Long-running streams should also
call `runtime.ping_chain(chain_id, interval=30.0)` so the chain stays
alive between calls.

### Nested spans

```python title="nested_span.py"
with nullrun.workflow("my-agent"):
    with nullrun.span("plan-generation"):
        plan = my_agent(user_input)
        with nullrun.span("tool-call"):
            tool.invoke(plan)
```

## `set_call_context()` — per-call data for the gate

```python title="set_call_context.py"
nullrun.set_call_context(
    model="claude-sonnet-4-6",
    tools=["send_email", "refund_customer"],
)
```

| Parameter | Type | Default | Effect when unset |
|---|---|---|---|
| `model` | `str \| None` | `None` | The gateway uses the workflow's default model rate. |
| `tools` | `list[str] \| tuple[str, ...] \| None` | `None` | The gateway evaluates the tool block against the protected function's own name only. |
| `max_output_tokens` | `int \| None` | `None` | The gateway uses its default output estimate. |

Call it inside a `with workflow(...)` block, before the protected
call. The gateway uses the model to price the reservation, and the
tool list to evaluate the tool block against the tools the call
actually intends to use.

`None` leaves the previous value unchanged. Pass `[]` to clear the
tool list.

## Approval rules and the action digest

Every protected call ships the function name, its arguments, and a
SHA-256 digest of the call's business impact. An approval rule that
inspects argument values names the parameter it cares about. The
gateway reads the live value from the request — there is nothing to
configure on the SDK side.

The digest binds the approval to the exact payload. If the amount or
the arguments change between the approval and the execution, the
gateway refuses.

## When to use what

| Task | API |
|---|---|
| Guard a function that calls an LLM or a tool | `@nullrun.protect` |
| Attribute a run to a workflow | `with nullrun.workflow("name"):` |
| Price the call and match the tool block against a tool list | `nullrun.set_call_context(model=..., tools=[...])` |
| Run a bounded overrun under a shared budget | `with nullrun.chain(uuid.uuid4(), op="start"):` |
| Nest a step in the trace | `with nullrun.span("name"):` |
| Attribute cost to one agent | `with nullrun.agent("name"):` |
| Fail fast on a bad config | `nullrun.init(fail_on_exit=True)` |
| Friendly exit at the entry point | `with nullrun.guard():` |
| Send every SDK error to your logging | `nullrun.on_error(handler)` |
| Track an LLM call the instrumentation cannot see | `nullrun.get_runtime().track_llm(...)` |
| Track a tool call the instrumentation cannot see | `nullrun.get_runtime().track_tool(...)` |
| Read the runtime state | `nullrun.get_runtime().status()` |

## Anti-patterns

!!! warning "Don't put `with nullrun.guard():` inside a protected body"
    The guard only catches errors raised inside its own block. A gate
    refusal is raised by the wrapper before the body runs, so it never
    reaches the block. The process exits with a raw traceback instead
    of the clean report.

!!! warning "Don't pass a cost to `track_llm`"
    Cost is recomputed on the gateway from the real token counts. The
    SDK sends tokens, not money.

!!! warning "Don't invent a `chain_id`"
    A `chain_id` must be a UUID v4. A readable slug raises
    `ValueError`.

!!! danger "Don't set `model` to lower the cost"
    `model` only selects which rate the gateway prices the
    reservation with. The charge comes from the real token counts, so a
    lower projected cost does not lower the bill.

## See also

- [SDK API](sdk-api.md) — the symbol table, exceptions, manual tracking
- [Human approval](../concepts/human-approval.md) — typed predicates and the action digest
- [Workflow context](../concepts/workflow.md) — chains, soft mode, and the workflow scope
- [Custom tracking](../how-to/custom-tracking.md) — when to track by hand
