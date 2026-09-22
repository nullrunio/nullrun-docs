---
title: Decorators & extractors
maturity: stable
description: Deep-dive reference for the Python SDK decorators (@protect, @guarded), the impact extractor factories (money_outflow, tool_params) used by the @sensitive(impact=...) advanced API, and the workflow / span / chain context managers they pair with. SDK 0.18.1: @protect is the only canonical public entry point — it auto-attaches tool_params; bare @sensitive is deprecated.
---

# Decorators & extractors

This page is the deep-dive reference for the SDK's runtime-API
surface — every decorator, impact extractor, and context manager
that affects **how a function call enters the gate**. The
top-level symbol table is in
[SDK API](sdk-api.md); this page explains the *contracts* each
symbol establishes with the gate.

**SDK 0.18.1 contract:** `@protect` is the single canonical public
entry point. It auto-attaches a default `ToolParamsExtractor` so
the wire payload carries `tool_name + params` for every protected
function — no second decorator is needed to opt in. The
`@sensitive(impact=...)` factory form remains supported as an
advanced API for library authors who need a typed impact extractor
(`money_outflow(...)`, `tool_params(...)`) and the digest-bound
approval flow. The bare `@sensitive` form is deprecated — it
emits `DeprecationWarning` in 0.18.x and is removed in 0.19.x.
See [The canonical API: `@protect` only](#the-canonical-api-protect-only)
below for the rationale and the migration path.

If you only want the "which one do I use?" answer, jump to
[When to use what](#when-to-use-what). If you want the full
contract for a single symbol, use the section headings below.

## The canonical API: `@protect` only

**The single canonical public entry point for the SDK is `@protect`.**
It is the gate. Every protected function call goes through the four
pre-execution gates (control plane / budget / span / sensitive-tool
policy) and emits a tool-call span event tagged with the masked
arguments. Starting in SDK 0.18.1, `@protect` also auto-attaches a
default `ToolParamsExtractor(include_all=True)` — the wire payload
carries `tool_name + params` for **every** protected function, not
only those that opted in via a second decorator.

What changed in 0.18.1:

- **`@protect`** stamps a default extractor and emits
  `params={"<arg_name>": <live_value>, ...}` on the wire for every
  call. Operators can match ToolParameters Approval Rules against
  these kwargs without any extra code.
- **`@sensitive(impact=...)`** (factory form) remains the advanced
  API for library authors — typed `BusinessImpact` + SHA-256
  `action_digest` for the digest-bound approval flow.
- **`@sensitive`** (bare form) is **deprecated** — emits
  `DeprecationWarning` in 0.18.x, removed in 0.19.x. It auto-attaches
  the same default extractor `@protect` already attaches, so the
  observable behaviour is identical. Migrate to `@protect` alone.

The split is intentional: the SDK collects facts (every kwarg goes
on the wire), the server decides what to do with them. Business
semantics — "this is a money tool", "this requires human approval" —
are expressed in NullRun policies, not in another decorator on the
function. See
[Human approval](../concepts/human-approval.md) for how operators
configure the typed predicates the gate evaluates.

## What's in scope

| Symbol | Type | Surface |
|---|---|---|
| `@protect` | decorator | eager (`from nullrun import protect`) — **canonical** |
| `@sensitive(impact=...)` | factory decorator (advanced API) | lazy (`from nullrun import sensitive`) |
| `@sensitive` (bare) | decorator | **deprecated in 0.18.1** — emits `DeprecationWarning`; removed in 0.19.x |
| `@guarded` | decorator | eager (via `__all__`) |
| `money_outflow(...)` | extractor factory | lazy (`from nullrun import money_outflow`) |
| `tool_params(...)` | extractor factory | lazy (`from nullrun import tool_params`) |
| `with workflow(...)` | context manager | lazy |
| `with span(...)` | context manager | lazy |
| `with agent(...)` | context manager | lazy |
| `with attempt(...)` | context manager | lazy |
| `with chain(...)` | context manager | lazy |
| `set_call_context(...)` | imperative setter | lazy |

Everything in this table participates in the **gate decision** for
at least one code path. Setters that only enrich observability
(`set_trace_id`, `set_operation_id`, etc.) are not covered here —
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
| 4 | `_enforce_sensitive_tool(...)` — `/execute` per-tool policy if `fn.__name__` is in the sensitive set | **fail-CLOSED** on transport error (a denied `charge_card` that runs when the policy engine is down is worse than a denied `charge_card` during an outage). Opt out via `NULLRUN_SENSITIVE_FAIL_OPEN=1`. | `NullRunBlockedException` on real block; on `NullRunTransportError` re-raises with source-specific `error_code` (NR-B001/NR-B002/NR-A003/NR-B005) | identical |

After the body completes, `@protect` calls
`track_tool(fn.__name__, metadata={"arguments": _safe_kwargs(kwargs)})`
to emit a tool-call span event tagged with the masked arguments.
Sensitive kwargs (PANs, tokens, etc., per `SENSITIVE_ARG_KEYS`)
are replaced with `"***"` **before** truncation so a long URL
never escapes the redaction window.

If any gate raises and the function body never ran, the wrapper
calls `_safe_cancel_active_execution(reason="tool_exception")` —
this hits `POST /cancel` to close the open Redis reservation
that `/gate` minted, so the budget doesn't leak via TTL expiry.

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

### `@protect` auto-attaches tool_params

Starting in SDK 0.18.1, every `@protect` stamps the function with a
default `ToolParamsExtractor(include_all=True)`. The kwargs of
every live call flow onto the wire under `params` without any
additional decorator — the gate sees them and matches them against
ToolParameters Approval Rules exactly the way bare `@sensitive`
used to. See
[Human approval → Typed predicates](../concepts/human-approval.md#typed-predicates).

```python title="protect_only_auto_attaches.py"
@nullrun.protect
def delete_user(uid: int) -> None:
    ...                  # params={"uid": <live value>} reaches the gate
```

This is the **recommended pattern** for any tool that should be
eligible for ToolParameters approval rules. To skip the auto-attach
(no `params` on the wire) — for example, when every kwarg is a
secret — wrap the function with the explicit
`@sensitive(impact=tool_params(include_all=False))` form below.

---

## `@sensitive` — advanced API for typed impact + digest

`@sensitive` has two forms. The factory form
`@sensitive(impact=...)` is the **advanced API**: it stamps a typed
`BusinessImpact` extractor on the function and forwards the SHA-256
`action_digest` to `/execute` so the gate's post-approval re-check
refuses the call if the live payload drifts from the approved
digest. The bare form is deprecated — see
[Deprecated form: bare `@sensitive`](#deprecated-form-bare-sensitive).

```python title="sensitive_factory.py"
@nullrun.sensitive(impact=money_outflow(argument="amount_cents"))
@nullrun.protect
def refund_customer(amount_cents: int, customer_id: str): ...
```

The factory form attaches a typed impact extractor to the
function. The wrapper reads it from the `_nullrun_extractor`
attribute and forwards the typed `BusinessImpact` + the SHA-256
`action_digest` to `/execute`. The gate's post-approval re-check
refuses the call if the live payload drifts from the approved
digest.

### The `impact=` parameter

Accepts one of two extractor objects.

#### `money_outflow(...)` — typed money impact

| Parameter | Type | Default | Notes |
|---|---|---|---|
| `argument` | `str` | required | Name of the parameter to extract the amount from. Positional or keyword — `inspect.signature(...).bind(...)` makes them equivalent. |
| `currency` | `str` | `"USD"` | ISO-4217 3-letter uppercase. Whitelist: `USD` `EUR` `GBP` `CHF` `CAD` `AUD` `JPY` `KWD` `BHD` `OMR`. Anything else raises `InvalidCurrencyError` at decoration time — **fail-CLOSED**. |
| `units` | `str` | `"minor"` | `"minor"` (the bound argument is already in minor units — `int` is the canonical type; `Decimal` accepted if integer-valued). `"major"` (the bound argument is a `Decimal` in major units — the SDK converts via `Decimal * 10**N` where `N = currency_minor_digits(currency)`). The discriminator is **explicit** so a refactor of the function signature from `int` to `Decimal` does not silently flip the meaning. |
| `extractor_id` | `str` | `"nullrun.money.path"` | Self-reported SDK provenance. Advisory only; the trust boundary is the digest round-trip. |
| `extractor_version` | `str` | `"1"` | Self-reported version. |
| `enforce_business_cap` | `bool` | `True` | Per-currency cap (default $1,000,000 USD per call). Above the cap the extractor raises `InvalidMoneyAmountError(reason="excessive")` so the call goes through the explicit human-approval path. Set `False` for batch-settlement tools that already have an approval flow. |

**What the extractor rejects outright:**

| Input | Why |
|---|---|
| `bool` | `bool` is a subclass of `int` in Python — without the check, `refund(amount=True)` would silently treat `True` as `1` cent. |
| `float` | IEEE-754 surprises are the entire reason `Decimal` exists. Pass `Decimal` for major units, `int` for minor. |
| Negative amount | A negative outflow would silently fall through every `op=gt` predicate (`-5000 > 5000` is always False). |
| `Decimal("50.005")` for USD | More fractional digits than the currency supports. Truncate explicitly with `value.quantize(Decimal("1E-2"))` to opt in to rounding; the SDK never rounds silently. |
| Amount above `2**63 - 1` | Wire-format `i64` upper bound — checked after conversion. |
| Amount above per-currency cap | `InvalidMoneyAmountError(reason="excessive")` unless `enforce_business_cap=False`. |

The result is `BusinessImpact(impact=MoneyImpact(...))` →
`compute_action_digest()` → 64 lowercase hex characters. The
digest MUST match the backend's calculation byte-for-byte; a
mismatch is a 403 `DIGEST_MISMATCH` on the post-approval re-check.

#### `tool_params(...)` — free-form argument bag

| Parameter | Type | Default | Notes |
|---|---|---|---|
| `param_extractors` | `dict[str, str] \| None` | `None` | Explicit `{rule_param: arg_name}` map. When set, **only** the listed args are captured under `rule_param` keys; everything else is dropped. Use this when the rule name diverges from the function arg name (e.g. `{"user_id": "uid"}`). `include_all` is ignored when this is set. |
| `include_all` | `bool` | `True` | Capture every kwarg verbatim. Set `False` (with `param_extractors=None`) for tools whose every kwarg is a secret the operator must never see. |

The two modes are mutually exclusive — passing both raises
`ValueError` at decoration time. The three effective extraction
modes (priority order):

1. `param_extractors` set → only those args under `rule_param` keys
2. `include_all=True` (default) → every kwarg as-is
3. neither → empty `params` (rare; tools that take no args but should still be eligible for `kind="tool_call"` approval rules)

**What the extractor filters out:**

- `***` masked sentinels (PII-masked values that would never match a real rule)
- `float` values (JSON round-trip is not lossless for IEEE-754)
- unsupported types (`set`, custom objects)

The wire shape is `BusinessImpact(impact=ToolCallParams(...))` and
shares the same `action_digest` contract as the money variant.

### Order of application

```python title="sensitive_order.py"
# Recommended: @sensitive outside (top), @protect inside (bottom)
@nullrun.sensitive(impact=money_outflow(argument="amount_cents"))
@nullrun.protect
def charge(amount_cents: int): ...

# Also works: @protect outside. Same observable behaviour.
@nullrun.protect
@nullrun.sensitive(impact=money_outflow(argument="amount_cents"))
def charge(amount_cents: int): ...
```

The recommended form is `@sensitive` outside so the registration
in `runtime.add_sensitive_tool(fn.__name__)` happens before the
`@protect` wrapper is built. `functools.wraps` makes both orders
work either way.

### When to use

| Tool category | Recommendation |
|---|---|
| Read-only tools (`get_weather`, `list_files`) | `@protect` alone — covers budget + span tracking. Auto-attached `ToolParamsExtractor` ships every kwarg on the wire. |
| Side-effect tools with bounded blast radius (`send_email`, `revoke_access`, `delete_user`) | `@protect` alone — auto-attached default extractor is enough for ToolParameters rules. |
| Money-moving tools (`refund`, `charge_card`, `transfer`) | `@protect @sensitive(impact=money_outflow(...))` — typed impact + `action_digest` for tamper-proof approval flow. |
| Tools where rule names ≠ arg names | `@protect @sensitive(impact=tool_params({"rule_param": "arg_name"}))` |
| Tools whose every kwarg is a secret | `@protect @sensitive(impact=tool_params(include_all=False))` to ship an empty `params` bag |
| Tools that need `kind="tool_call"` envelope with no extractor | `@protect @sensitive` (bare, **deprecated**) — emits `DeprecationWarning` in 0.18.x. Use `@protect @sensitive(impact=tool_params(include_all=False))` instead. |

In 0.18.1+ the bare `@sensitive` form is no longer required for
any ToolParameters predicate — `@protect` already ships the kwargs
on the wire. Reach for `@sensitive(impact=...)` only when you need
the typed `BusinessImpact` envelope (money / tool_parameters) and
the digest-bound approval flow.

Without `@protect` (and without an explicit
`runtime.add_sensitive_tool(fn.__name__)`), the `_enforce_sensitive_tool`
gate is a no-op — the function body runs immediately after
`/gate`. This violates the fail-CLOSED contract for any
irreversible action.

---

## Deprecated form: bare `@sensitive`

```python title="sensitive_bare_deprecated.py"
@nullrun.sensitive          # DeprecationWarning in 0.18.x; removed in 0.19.x
def delete_user(uid: int): ...
```

The bare form auto-attaches the same `ToolParamsExtractor`
that `@protect` already attaches, so the observable behaviour
is identical to `@protect` alone in 0.18.x. Use `@protect` and
delete the bare `@sensitive`:

```python title="sensitive_bare_migration.py"
@nullrun.protect            # canonical form — no @sensitive required
def delete_user(uid: int): ...
```

Why the deprecation:

- `@protect` is the gate — every protected tool needs it. Adding
  `@sensitive` on top was a second decorator that asked the same
  question twice.
- The default extractor (`include_all=True`) is the only thing
  bare `@sensitive` contributed, and `@protect` stamps it
  automatically in 0.18.1+.
- The business interpretation of those params belongs to NullRun
  policy (ToolParameters Approval Rules), not to a second
  decorator on the SDK side.

The legacy behaviour is preserved in 0.18.x with a
`DeprecationWarning`. Removal is scheduled for 0.19.x. The
factory form `@sensitive(impact=...)` is **not deprecated** —
it remains the advanced API for typed impact + digest-bound
approval flow.

---

## `with nullrun.handle():` (and `@guarded`) — friendly-exit wrapper

The **canonical form is `with nullrun.handle():`** — it makes the
scope explicit and prints the structured four-line developer report
on any `NullRunError`. `@guarded` is the decorator equivalent for
the same behaviour.

**Parameters: none (decorators and context managers).** `handle()`
accepts an optional `exit_code=` keyword (default `1`).

```python title="handle_canonical.py"
import nullrun
from nullrun import protect

@protect
def my_agent(prompt: str) -> str:
    return call_llm(prompt)


if __name__ == "__main__":
    with nullrun.handle():
        print(my_agent("hello"))
```

For decorator-style usage, `@guarded` is the alternative — same
behaviour, function-scoped:

```python title="guarded_basic.py"
@nullrun.guarded
@nullrun.protect
def my_agent(prompt: str) -> str:
    return call_llm(prompt)
```

### What they do

Any `NullRunError` raised inside the wrapped function (or inside
the `handle()` block) is caught, rendered as the **structured
four-line developer report** (`[error_code]` + `what` + `where` +
`why` + `how to fix`), printed to **stderr**, and the process
exits with code `1`.

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

### Order of application

`@guarded` is always **outside** `@protect`:

```python title="guarded_order.py"
# CORRECT
@nullrun.guarded
@nullrun.protect
def my_agent(prompt): ...

# WRONG — @guarded below @protect does not protect the body
@nullrun.protect
@nullrun.guarded
def my_agent(prompt): ...
```

### When to use

For **top-level entry points** in scripts and CLIs: instead of a
raw traceback on `NullRunConfigError(NR-C001)` at the first gate
call, the operator sees the structured four-line developer report
and the process exits cleanly. In libraries and long-running
services, prefer `try/except NullRunError` — `handle()` / `@guarded`
exit the process, which isn't appropriate there.

The context-manager form `with nullrun.handle():` is the
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
| `with span(name=None)` | `name: str \| None` | Child span derived from the active parent `SpanContext`. No-op if no parent is active (bare `with span(...)` outside any workflow/protect block keeps the legacy fallback). |
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
| `model` | `str \| None` | `None` (no change) | Backend receives the literal `"budget-precheck"` and falls back to the default pricing rate. Per-model budget tiers cannot fire. |
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

## When to use what

| Task | API |
|---|---|
| Wrap a function that calls an LLM or tool (canonical) | `@nullrun.protect` (no parameters) — auto-attaches default `ToolParamsExtractor` |
| Mark a money-moving tool for typed approval + digest | `@nullrun.protect @nullrun.sensitive(impact=money_outflow(argument="amount_cents", currency="USD"))` |
| Mark a tool where rule names ≠ arg names | `@nullrun.protect @nullrun.sensitive(impact=tool_params({"user_id": "uid"}))` |
| Mark a tool where every kwarg is a secret | `@nullrun.protect @nullrun.sensitive(impact=tool_params(include_all=False))` |
| Legacy code with bare `@sensitive` | Migrate to `@protect` alone — emits `DeprecationWarning` in 0.18.x; removed in 0.19.x |
| Top-level script entry (friendly exit) | `with nullrun.handle():` (preferred) — `@nullrun.guarded` is the decorator alternative for the same behaviour |
| Multi-step agent run (cost + trace per workflow) | `with nullrun.workflow("agent-name"): ...` |
| Per-call model name and tools for `/gate` | `nullrun.set_call_context(model=..., tools=[...])` inside `with workflow` |
| Soft-mode budget (controlled overdrafts) | `with nullrun.chain(uuid.uuid4(), op="start"): ...` |
| LangGraph auto-tracking | (auto on first `@protect` call; legacy manual wrapper `from nullrun.toolbox.langgraph import wrapper` is deprecated) |
| Manual LLM tracking (custom client) | `nullrun.track_llm(input_tokens=..., output_tokens=..., model=...)` |
| Manual tool-call tracking | `nullrun.track_tool(tool_name=..., duration_ms=..., metadata=...)` |
| Custom business event | `nullrun.track_event("agent.milestone", step=..., elapsed_secs=...)` |
| Audit log read | `runtime.audit.list(AuditQuery(event_type=..., since=..., limit=...))` |
| Global error hook (Sentry, OTel) | `nullrun.on_error(my_handler)` — returns an idempotent unregister callable |
| Snapshot runtime state | `nullrun.status()` — frozen `NullRunStatus` dataclass |
| Graceful exit (WS close, flush events) | `nullrun.shutdown()` or `nullrun.shutdown(flush=False)` in tests |

---

## Order of application — cheat sheet

```python title="order_cheatsheet.py"
# ─── Sensitive money tool (advanced API) ───
@nullrun.sensitive(impact=money_outflow(argument="amount_cents", currency="USD"))
@nullrun.protect
def refund(amount_cents: int): ...

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

# ─── Top-level script entry with friendly exit (handle() preferred) ───
import nullrun
from nullrun import protect, shutdown

@protect
def main(prompt): ...

if __name__ == "__main__":
    try:
        with nullrun.handle():               # canonical — 4-line report + exit 1
            print(main("hello"))
    finally:
        shutdown()

# ─── Full layering: chain → workflow → call context → @protect ───
# No init() / init_or_die() — runtime is created lazily on the first
# @protect call. NULLRUN_API_KEY must be set in the shell.
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

!!! danger "Don't put `@protect` outside `@sensitive`"
    Either order works, but the recommended convention is
    `@sensitive` outside so registration in
    `runtime.add_sensitive_tool` happens before the `@protect`
    wrapper is built. Both produce identical observable behaviour
    today; future shape changes may not.

!!! note "Don't write bare `@sensitive` in new code (0.18.1+)"
    Bare `@sensitive` is deprecated. `@protect` auto-attaches the
    same default `ToolParamsExtractor`, so every tool that used to
    be `@protect @sensitive` is now `@protect` alone. The factory
    form `@sensitive(impact=...)` remains the advanced API for
    typed impact + digest-bound approval.

!!! warning "Don't put `@guarded` below `@protect`"
    `@guarded` only catches errors raised inside the function it
    decorates. A bare `@guarded` underneath `@protect` is a no-op
    for gate-time errors — the exception is raised by the
    `@protect` wrapper, never reaches the user's function, and
    bubbles past `@guarded` unhandled.

!!! warning "Don't pass `cost_cents` to `track_llm`"
    The SDK strips it before sending. Cost is recomputed on the
    backend from `input_tokens + output_tokens + org pricing policy`.
    `tokens` is the only valid unit on the wire.

!!! warning "Don't use `money_outflow(argument="amount_cents")` on a `float` parameter"
    `float` is rejected outright. `Decimal` for major units, `int`
    for minor units — the unit discriminator (`units="minor"` vs
    `units="major"`) is **explicit** and does not flip when you
    change the type annotation.

!!! danger "Don't use `money_outflow(units="major")` on an `int` parameter"
    `int` is rejected. `int` is only valid under `units="minor"`.
    The explicit unit discriminator is the same review that
    rejected implicit-from-type — a future refactor of the
    signature (`int` → `Decimal`) must not silently flip the
    meaning from cents to dollars.

!!! warning "Don't call `set_chain_id("my-custom-id")`"
    `chain_id` MUST be a UUID v4 string per CLAUDE.md §6. The
    backend's race guard does not validate format — non-v4 ids
    silently auto-register as new ACTIVE chains. Use
    `with nullrun.chain(uuid.uuid4(), op="start")` to let the SDK
    validate.

!!! warning "Don't put `@sensitive` outside any `with workflow(...)` scope in production"
    Bare `@sensitive` outside a workflow scope carries the sentinel
    `__nullrun_unknown__` as the displayed `workflow_id`. The
    dashboard renders this as "unknown workflow" — operators can't
    attribute the call to a real policy.

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
  `@sensitive` vs `ToolBlock`, why the SDK does not ship a built-in
  sensitive list
- [Human approval](../concepts/human-approval.md) — typed predicates
  (`money_amount`, `tool_parameters`) and `action_digest`
- [Workflows](../concepts/workflow.md) — dashboard-side view of a
  workflow (budget cap, API keys, executions, traces)
- [Custom tracking](../how-to/custom-tracking.md) — when to use
  `track_llm` / `track_tool` / `track_event` instead of
  auto-instrumentation
- [Use with LangGraph](../how-to/langgraph.md) — `wrapper()` helper
  and the LangGraph extra