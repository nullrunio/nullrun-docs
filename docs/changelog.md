---
title: Changelog
description: Every released version of the NullRun Python SDK, with the changes a reader of these docs can observe — new API surface, behaviour changes, and fixes.
maturity: stable
---

# Changelog

Every released version of the `nullrun` Python SDK, newest first. Entries
cover what someone building on NullRun can observe: the API surface, the
behaviour a protected run exhibits, and the wire contract.

The docs are the source of truth for **how** each of these behaves —
this page records **when** it changed. A version listed here is
described in full in the chapters it affects; if a symbol appears in an
entry, it is documented on one of those pages.

!!! info "Reading version numbers"

    The SDK is versioned `0.MINOR.PATCH`. The **minor** position is
    where the public surface moves — a symbol appears, changes shape, or
    goes away. The **patch** position carries behaviour fixes and
    additions that do not alter the surface.

    All versions below the current one are available on PyPI:

    ```bash
    pip install nullrun==0.24.0
    ```

## 0.24.0 — 2026-11-08

The enforcement path stopped swallowing refusals. A gate that answered
"no" could be turned into `None`, and `None` is read by every caller as
"yes". A refused `/track` could be logged and returned as an ordinary
call. A LangChain callback dropped the refusal on the floor, so the
agent got the call for free.

The control plane got a second fix. The approval push read the unsigned
outer body — the bytes the HMAC never covered — and handed them to the
handler that releases a gate parked waiting for a human. The privileged
branch now requires an authenticated frame and reads the verified
payload only.

There is no wire-format change. Every new error code the SDK names is a
code the gateway already sends, and the one code that is new to both
repos, `APPROVAL_TOOL_MISMATCH` (HTTP 409), shipped together with its
gateway half.

### Changed

- **`check_workflow_budget` lost its `use_gate_cache` parameter.**
  Passing it now raises `TypeError` — remove the argument. The
  in-process gate cache is gone. Every call is its own `/gate` call with
  its own reservation.

- **`NULLRUN_SENSITIVE_FAIL_OPEN` opens nothing on its own.** The
  switch is still a whole-system switch, but the tools it may open are
  now an explicit, code-level list. The list is empty by default, so
  the switch alone opens nothing and every tool stays fail-CLOSED.
  Four runtime methods drive it:

  ```python
  runtime.register_fail_open_tools(["charge_card"])
  runtime.remove_fail_open_tool("charge_card")
  runtime.get_fail_open_tools()
  runtime.is_fail_open_allowed("charge_card")
  ```

- **A gate refusal now escapes the LangChain / LangGraph callback.**
  The refusal is re-raised instead of being caught by a blanket
  `except Exception`. A cosmetic failure is still swallowed at DEBUG —
  only a refusal escapes.

- **An indeterminate gate decision is a refusal, not a permission.**
  When the SDK's own code faults while asking the gateway, the SDK
  raises `NullRunGateIndeterminateError` (NR-P004) instead of returning
  "no decision, carry on".

- **The write-ahead log path changed.** The default is now
  `<tempdir>/nullrun-<user>-<key>.wal`. Both scope tokens are SHA-256
  digests, so the API key never reaches a path every user on the host
  can list. `NULLRUN_WAL_PATH` still wins outright.

- **`api_key_prefix` renders as a fingerprint.** The public field keeps
  its name; the value is the first eight hex characters of the SHA-256
  digest of the key. The log label is `api_key_fp=`. Log parsers that
  matched the old raw prefix must change.

- **The MCP tool-annotation cache window is 30 seconds.** A failed
  refresh no longer presents the previous snapshot to the gateway — the
  gateway gets the unknown shape the adapter uses for a tool it has
  never seen, and falls back to its own classifier. Pass
  `cache_seconds=0` for no staleness at all.

- **Three new public exceptions.**
  `NullRunGateIndeterminateError` (NR-P004),
  `NullRunUnknownActionError` (NR-P005) and
  `NullRunApprovalToolMismatchError` (NR-A017) are exported from the
  package root. `NullRunChainError` now covers the gateway's
  `CHAIN_KEY_MISMATCH` refusal.

- **Six new metric counters** are exported in `to_dict()`:
  `gate_indeterminate_total`, `unknown_action_total`,
  `policy_gate_indeterminate_total`, `ws_unverified_approval_total`,
  `ws_unverified_frame_total` and `dropped_llm_call_no_reservation`.

### Fixed

- **A refused `/track` reaches the application.** The SDK asked the
  wrong question — it decided open-vs-closed by exception class while
  the gateway decides by error code. A refusal now raises, and the
  auto-instrumentation layer stops swallowing it. The payload is written
  to the write-ahead log before the raise, so a refusal is raised *and*
  recoverable.

- **A reservation id the SDK cannot bind is a refusal.** A gate answer
  carrying a `reservation_id` that is not a UUID now raises
  `NullRunMalformedGateResponseError` instead of proceeding with no
  reservation.

- **An SDK-internal fault in the `@protect` gate is a refusal.** The
  decorator's catch-all raised a transport-shaped error that rendered as
  HTTP 429 and category "decision". It now raises
  `NullRunGateIndeterminateError` and is counted on its own counter.

- **The LangChain callback obeys the same fail-CLOSED table as
  `@protect`.** `NullRunAuthenticationError`,
  `NullRunUnclassifiedRefusalError` and `NullRunRateLimitRedisError`
  now raise instead of vanishing through the callback.

- **Every MCP tool call runs its own `/gate` pre-flight.** The second
  and later MCP tool calls in one scope ran no pre-flight: no budget
  check, no reservation, no spend reserved for those calls.

- **The MCP adapter derives one envelope from the tool call.** The MCP
  path sent no `business_impact` and no `action_digest`, so an approval
  on that path could not be spent at all. The adapter now derives one
  envelope from the call it is about to make, plus that envelope's
  digest, and puts both on the wire.

- **The write-ahead log is scoped per user and per key.** The path was
  the same string for every user and every organization on the host, so
  two runtimes on one file destroyed each other's undelivered events.

- **The approval push reads the verified payload, not the outer body.**
  An unauthenticated approval frame is refused, counted and logged at
  ERROR, and the waiter stays parked and fails closed on the approval
  timeout.

- **A control-plane frame the client could have verified is refused.**
  A frame that arrives unsigned, or with a signature but no timestamp,
  is refused before any branch reads a field out of it.

- **An unknown control-plane action is refused, not silently dropped.**
  The dispatcher now raises `NullRunUnknownActionError` instead of
  logging and returning.

- **The error-code catalog names a class the dispatcher can build.**
  The catalog lagged the gateway registry by 34 codes, and the
  blocked-family dispatch arm matched by identity, so every typed
  subclass fell through to a generic fallback that raised `TypeError`.

- **Redaction follows the credential, not only the argument name.** A
  value-shaped pass runs beside the name-based one, so a secret that
  arrives under a name nobody listed is scrubbed.

- **No character of the API key reaches a log line.** Three places
  printed a fragment of the key, and they disagreed about how much. One
  helper answers it now.

- **The production detector is not a substring test.** A host that
  merely contained a dev marker was classified non-prod. Four ordered
  rules now decide.

- **The CI installs from the lock and pins every action.**

## 0.23.0 — 2026-10-29

Two enforcement paths that could not complete their own contract are
closed. The MCP path could not finish an approval round trip: a retry
after the operator approved was forwarded to the MCP server, so the
gateway never saw the grant. The zero-code LLM path booked the call
only after the provider had answered — the `llm_call` event is the only
thing that moves the budget counter, so a call the ceiling was supposed
to stop was counted instead of stopped.

There is no wire-protocol change. The public surface grows by ten
keyword-only parameters across four public methods, and one changed
return value.

### Added

- **`MCPAdapter.call_tool` can carry an approval grant.** The method
  gains three named keyword-only parameters — `approval_id`,
  `business_impact`, `action_digest` — placed before `**passthrough`
  so they can never fall into the passthrough and be forwarded to the
  MCP server.

- **`NullRunRuntime.execute` gains `approval_id` and
  `tool_arguments`.** Both are appended after the existing parameters,
  so the positional order above them is unchanged. Each key reaches the
  wire only when the value is not `None`.

### Changed

- **`check_workflow_budget` returns the reservation id.** The method
  gains `model`, `estimated_tokens`, `max_output_tokens` and
  `use_gate_cache`, and its return type changes from `None` to
  `str | None` — the server-minted reservation the gateway settles
  when the matching `/track` arrives, or `None` when no reservation was
  minted. Callers that ignored the return value are unaffected.

- **`NullRunRuntime.track` gains `reservation_id`.** The reservation
  travels with the cost event explicitly rather than through a
  context variable, which is one slot per task — two concurrent calls
  would swap reservations.

- **The zero-code LLM path reserves before the provider request.** A
  call the ceiling rejects never reaches the provider; the request is
  not sent at all. This is visible: a capped zero-code caller sees
  refusals where it saw successful calls that were billed anyway.

### Fixed

- **The canonical argument bag reaches the wire.** The tool arguments
  travelled only as the legacy `input` field, so every params-based
  rule saw "no bag" and the approval decision had no argument snapshot
  to bind to. The same dict now reaches the wire as both `input` and
  `tool_arguments`.

## 0.22.2 — 2026-10-16

A status field that structurally could not report the failure it
existed to report, a packaging extra the SDK's own error message told
users to install but that was never declared, and a pre-flight that
priced at the input rate and so silently under-reserved every real LLM
call. None is a wire change.

### Changed

- **`NullRunStatus` reflects a gateway that has actually been
  attempted.** A backend unreachable since `init()` used to read
  `backend_reachable=None`, so the degraded headline never fired.
  "Answered" means transport-level, not HTTP-2xx — a 402, 403 or 429
  is the gateway replying and stays reachable; only DNS, refused, TLS
  or timeout sets it false.

- **`pip install nullrun[websocket]` installs `websockets`.** The
  extra is declared with a floor of 14.0.

- **`set_call_context(max_output_tokens=…)` reaches `/gate`.** The
  pre-flight always sent `estimated_tokens=1`, which prices at the input
  rate and covers no output at all. The caller's declared cap is sent
  when set, and the key is absent — not present-and-null — when it is
  not.

## 0.22.1 — 2026-10-15

The SDK's public exception surface is restored. A QA pass found 24
classes the SDK raises that were not importable from the top-level
`nullrun` namespace. The classes existed, and enforcement was never
affected — only the documented public name was missing.

### Added

- **24 more exception names are reachable via `from nullrun import X`.**
  The names are also added to `__all__`, so tab-completion and
  `from nullrun import *` reach them. Code that imports a missing name
  now succeeds.

### Fixed

- **`on_policy_invalidated` fires on every WebSocket message.** The
  wrapper was an un-awaited coroutine, so the log line and the
  user-supplied callback never ran.

## 0.22.0 — 2026-10-09

The SDK's enforcement question can go to a local box that holds a
signed lease instead of to `api.nullrun.io`. The write-ahead log is
reworked around three loss paths: a `kill -9` while a refused event
was held, a 200 batch that hid per-item refusals, and a recovery that
unlinked the log before the events were provably safe.

Minor, not patch: the `/track` wire loses a field, and `/track` batch
refusals classify by whether the gateway already booked the spend.

### Changed

- **A `CONSUME_OVERBUDGET` refusal that the gateway already booked is
  delivered, not quarantined.** The exception now carries a `recorded`
  tri-state (`True` / `False` / `None` for unparseable bodies) so a
  caller can tell the two apart. Code that watched the dead-letter
  queue for these events no longer sees them there.

- **`/track` no longer sends `cost_cents`.** The field was always
  zero and the gateway ignores it. `local_cost_cents` in the return
  value is unchanged.

- **4xx classification happens before quarantine, with a different
  answer per class.** `408` and `429` are re-queued and never
  dead-lettered. `401` and `403` stay in the log with a "blocked on
  the key" line — the data is valid and the key is rotated or revoked.
  `413` is the batch, not the events: the batch is halved and resent.
  `400` and `422` are bisected to a single event, so exactly one event
  is lost rather than the whole batch.

- **A held refusal survives `kill -9`.** The holdover is now in
  `<wal>.holdover` — deliberately not `.wal` and not `.inflight`.
  Recovery loads it as a hold, not a replay.

- **The `/track` batch path forwards the `provider` label.** Cached
  pricing differs by provider, and the two paths now agree.

- **The local box as the gate is opt-in.** Set `NULLRUN_EDGE_URL` and
  the enforcement question goes to a box holding a signed lease instead
  of to `api.nullrun.io`. `NULLRUN_EDGE_LEASE_ID` is required, not
  discovered — a box that chose its own budget enforces a number nobody
  granted. The mode refuses a silent fallback to the cloud, refuses a
  caller that writes the money, and treats an unreachable box as a
  refusal rather than a pass.

### Security

- **The SDK never puts a price on the wire.** The field is absent from
  both a minimal and a fully populated payload.

- **The write-ahead log's guarantees are explicit, private and
  observable.** Files are created `0600` rather than through the
  process umask, mutations are serialised with an advisory lock, and
  the dead-letter size cap deletes nothing: at the cap the append is
  refused.

## 0.21.0 — 2026-10-02

The approval round trip closes. An operator approves an action and the
agent still cannot run it: the SDK sent a constant sentinel instead of
the business-impact envelope the gateway was looking for, and
classified refusals by what the SDK's wrapper assumed rather than by
what the wire said.

Minor, not patch: `BusinessImpact.tool_call()` is restored, the
`/track` path raises typed enforcement rejections where it dropped them
silently, and the `/gate` pre-flight routes through the typed
dispatcher.

### Added

- **`BusinessImpact.tool_call()` is back.** Importable from
  `nullrun.business_impact`. The constructor emits exactly what the
  gateway's internally-tagged serialization produces, including
  `extractor_id` and `extractor_version`.

### Changed

- **The v3 `/track` single path raises typed enforcement rejections
  instead of dropping them.** A 422 `CONSUME_OVERBUDGET` used to be a
  warning log line and a return value that treated the call as
  successful at the agent layer. It now raises
  `NullRunConsumeOverbudgetError`. Network errors and 5xx that name no
  enforcement failure still drop and log.

- **The `/gate` pre-flight types its refusal instead of assuming
  budget.** A rate-limit block, a tool block and a circuit-breaker
  trip used to reach the caller as `NullRunBudgetError` (NR-B004),
  which sends the operator looking for a spend-cap misconfiguration
  when the actual cause is a throttle policy. The dispatcher routes by
  wire code. A response with no machine-readable code still raises
  `NullRunBudgetError`.

### Fixed

- **`@protect` binds approvals to something.** Since 0.18.5 every
  `@protect` call sent a constant `{"kind": "none"}` sentinel; a
  constant hashes to a constant, so the digest the gateway stored on
  the approval row matched the digest it recomputed at `/execute` for
  every tool — while binding the approval to nothing at all. The
  envelope is now carried on the call context, sent alongside the
  digest, and built before the `/gate` pre-flight so both hops hash
  the same bytes.

- **`status().ws_connected` reads a real attribute.** It was
  structurally pinned to `None`, so the never-established, live and
  dropped states collapsed into one.

## 0.20.0 — 2026-10-01

Every gate refusal is classified, and an unclassifiable one raises.
The SDK could read a body with no `category` as a permission.

Minor, not patch: an unclassifiable refusal now **raises** where
0.19.0 let the call proceed. That is a working loop becoming a
throwing one.

### Added

- **`on_denied` selects the shape of a `denied` refusal and nothing
  else.** Default `"raise"`. Set `"message"` to get a
  `NullRunDeniedError` carrying the server-authored `agent_message` —
  the only text the SDK guarantees is safe to relay to a model. `budget`
  and `halt` keep their own exceptions even with the flag set.

### Changed

- **A `/gate` body must state who decided before it counts as a
  verdict.** A body whose `decision_source` is absent or unrecognised
  raises `NullRunMalformedGateResponseError`. A hand-written `/gate`
  test double must now include `"decision_source": "gateway"`.

- **`NULLRUN_SENSITIVE_FAIL_OPEN` is refused against production**
  unless `NULLRUN_ALLOW_SENSITIVE_FAIL_OPEN=1` is set as well. The
  guard refuses the bypass rather than raising, so enforcement falls
  back to its own fail-CLOSED default and the attempt is logged at
  ERROR with a metric.

- **`NULLRUN_SKIP_BUDGET_CHECK` outside production logs and
  increments a metric** when it skips the check. Enforcement behaviour
  is unchanged.

- **`/execute` refusal bodies carry `category` and `agent_message`.**
  Additive on the wire.

### Fixed

- **`@protect` no longer loses a LangChain tool when it is the outer
  decorator.** Applied to a `@tool` result, `@protect` wrapped the
  object with `functools.wraps` and returned a plain function, so
  `.invoke`, `.name` and `.args_schema` were gone and an agent loop
  could not bind the tool. A tool the loop cannot see raises no
  refusal. Both decorator orders now gate identically.

## 0.19.0 — 2026-09-30

The SDK-side bypasses found by an audit of the enforcement path are
closed: the gate answering the agent "allowed" on calls it had actually
blocked or never checked.

### Removed

- **`NullRunRuntime.execute(..., mode="inline")` is gone.** It returned
  a synthesised local allow without contacting the gateway, so budget,
  rate-limit and tool-block policies were all skipped. It now raises
  `NullRunConfigError` (NR-S001). There is no replacement — every call
  goes through `/execute`. Drop the argument; `mode="auto"` (the
  default) already always contacts the gateway.

- **`register_strict_mode_forced` and `is_strict_mode_forced` are
  gone.** They existed only to force strict mode past the inline fast
  path, and had zero callers.

### Changed

- **`MCPAdapter(runtime=None)` no longer means "do not gate".**
  `call_tool` was conditional on the runtime being present, and the
  runtime defaulted to `None` — so a default-constructed adapter called
  the MCP server with no `/execute` round-trip at all. `runtime=None`
  now means "resolve the global runtime", resolved lazily at
  `call_tool`. A missing API key raises rather than degrading to an
  ungated call. Passing `runtime=` explicitly still works and still
  wins.

### Fixed

- **A real gate decision is no longer treated as a transport
  fail-open.** The LangChain / LangGraph callback swallowed
  `NullRunBlockedException` alongside transport errors. Enforcement
  exceptions are now re-raised through a deferred handoff to the
  `@protect` boundary.

- **A skipped pre-flight gate is countable.** The no-op increments
  `control_plane_no_workflow_total` /
  `budget_preflight_no_workflow_total` instead of being
  indistinguishable from normal operation.

## 0.18.5 — 2026-09-26

The public surface is reduced to the smallest set that still does the
job. Four entry points collapse into two, and a set of internals stops
being importable.

### Changed

- **`nullrun.guard` replaces `nullrun.handle`.** Same `@contextmanager`
  body: it catches `NullRunError`, re-raises `WorkflowKilledInterrupt`
  untouched, prints a developer-facing report, and exits non-zero on
  failure. See [Error handling](concepts/error-handling.md) for the
  full context-manager set and where `guard` sits among them.

- **`nullrun.init(fail_on_exit=True)` replaces `init_or_die()`.**
  Fail-fast is now a keyword argument on `init` rather than a separate
  function. The default is `False`, which preserves the raise-on-bad-config
  behaviour that embedders want.

- **`nullrun.shutdown()` is registered automatically.** `init()` arranges
  for a clean WebSocket close at process exit, so a long-running script
  no longer needs an explicit shutdown call. Calling it yourself is
  still valid and still idempotent.

- **Install is a single line.** Per-framework install groups are gone;
  `pip install nullrun` is the whole instruction. The framework
  auto-detection in [Framework integrations](how-to/llm-frameworks.md)
  is unchanged.

### Removed

These names are no longer importable from the top-level `nullrun`
namespace. At 0.18.5 the top-level namespace held exactly:

```text
__version__, init, protect, shutdown, on_error, guard,
NullRunError, NullRunAuthError, NullRunConfigError,
NullRunBackendError, NullRunBudgetError, NullRunToolBlockedError,
WorkflowKilledInterrupt, NullRunWorkflowKilledError,
NullRunMcpDestructiveBlockedError,
NullRunMcpReadonlyBypassBlockedError,
NullRunMcpApprovalRequiredError,
NullRunApprovalDbUnavailableError,
format_user_message, set_user_message
```

- `nullrun.status()` — the snapshot is reached through
  `nullrun.get_runtime().status()`, which returns the same
  `NullRunStatus` dataclass. `NullRunStatus` itself remains importable
  as a type.
- `@nullrun.guarded` — the decorator form is `with nullrun.guard():`.
- `nullrun.auto_instrument`, `nullrun.is_auto_instrumented`, and the
  module-level `track_event` alias. The `runtime.track_event` method is
  unaffected.
- `NullRunCallback` from the lazy-export table. The framework
  integrations do not need it.

The wire contract is unchanged from 0.18.0.

## 0.18.2 — 2026-09-22

`@protect` is established as the single entry point. Every call routes
through the execute endpoint unconditionally — there is no opt-out and
no per-tool registry to maintain.

```python
import nullrun

nullrun.init()

@nullrun.protect
def my_tool(query: str) -> str:
    ...
```

See [Decorators & extractors](reference/decorators.md) for the full
decorator reference and [Tool policies](concepts/tool-policies.md)
for what the gate evaluates.

## 0.18.1 — 2026-09-22

Aimed squarely at the moment a developer first runs an example and it
does not work.

- **A four-line error report on the fail-fast paths.** A configuration
  or gate failure at startup prints what failed, where it failed (wire
  endpoint, status code, transport source), why it failed (the
  underlying exception and its machine `error_code`), and what to do
  about it. The end-user-facing message is still the headline, so an
  end-user deployment still sees a single clean sentence. See
  [Troubleshooting](troubleshooting.md).

- **A warning when a protected tool fires 50 times with no model
  activity.** The usual cause is a tool wired up without the agent loop
  that feeds it, which otherwise bills nothing and looks like it works.

## 0.18.0 — 2026-09-21

- **Approved actions are consumed on success.** When an action runs
  after approval, the grant is closed automatically. Grants left open
  past their expiry no longer accumulate, so the approvals surface
  reflects only what is actually waiting on a human.

## 0.17.1 — 2026-09-15

- **Every gate call carries its own operation id.** A single id is no
  longer reused across calls in the same scope, which removes a class
  of spurious budget errors where an unrelated call inherited the identity
  of the first one. The error codes in
  [Error codes](reference/errors.md) are unchanged.

## 0.17.0 — 2026-09-12

- **The circuit breaker serialises sync and async callers against each
  other.** A threaded call and an `asyncio` call on the same breaker
  instance previously took different locks, so their state transitions
  could interleave. Both paths now contend on one lock. See
  [Circuit breaker](concepts/circuit-breaker.md).

- **The impact helpers resolve off the top-level `nullrun` namespace**
  rather than needing a deep import into a private module. The helpers
  that [Sensitive tools](concepts/sensitive-tools.md) describes are
  what this fixes; the exception they were raising on first call is
  gone.

## 0.16.x — August–September 2026

The hardening series. The surface settled here; everything above is a
change to it.

- **Kill propagates as an exception rather than an exit.** A
  `WorkflowKilledInterrupt` raised by [Kill](concepts/control-plane.md)
  is not swallowed by an enclosing error handler, so an agent that is
  stopped from the control center stops. See
  [Control plane](concepts/control-plane.md).

- **Policy fetches fail closed.** A policy the gate cannot retrieve is
  a refusal, not a pass. The enforcement path fails closed: the tool
  block, the aggregate rate limit and the budget check all refuse when
  their signal is missing. See [Policies](concepts/policies.md).

- **Cost accounting is decimal, not floating point.** Amounts are
  serialized without binary-float drift, so a reserved cost and its
  consumption net to zero. See [Budgets](concepts/budgets.md).

- **Reservations are released on the exception path.** A protected call
  that raises leaves no reservation behind.

---

Reports something that does not match what you are reading here? The
[GitHub](https://github.com/nullrunio/nullrun-docs) link in the footer
points at this docs repository. Open an issue there.
