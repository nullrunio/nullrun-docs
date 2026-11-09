---
title: Circuit breaker
maturity: stable
description: The SDK-side circuit breaker — it opens after repeated failed event flushes, short-circuits the flush while open, and recovers after a cooldown.
---

# Circuit breaker

The SDK ships a client-side circuit breaker in the transport layer. It
watches the event flush the SDK makes to the gateway. After a run of
failed flushes it opens and stops sending, so an unreachable gateway
does not turn into a hang. It closes again after a cooldown.

A policy refusal and a breaker trip are different things:

- A **policy refusal** is the gateway answering "no". The gate
  evaluated your rules and blocked the call.
- A **breaker trip** is the SDK noticing that the gateway is not
  answering at all.

## States

| State | What happens |
|---|---|
| **Closed** | The flush goes out normally. A transport failure raises the failure count. A success resets it. |
| **Open** | The flush is skipped. The events stay queued and the SDK retries them after the cooldown. |
| **Half-open** | The breaker lets one probe through. A success closes it. Another failure opens it again. |

The breaker keeps its state in the process that runs it, so two
processes run two breakers.

## When it opens

The breaker opens after a run of consecutive transport failures: a
timeout, a refused connection, a 5xx. The threshold is the failed-flush
limit, 10 by default.

The half-open probe waits 30 seconds, plus a random delay of up to 5
seconds, so two processes do not probe at the same instant. One probe
runs at a time.

While the breaker is open the SDK keeps the pending events and retries
them on a later flush. The agent keeps running.

## What it raises

Nothing into your code. The breaker sits on the event flush, in a
background thread. When it is open, the SDK logs a warning and moves on.

`BreakerError` and `BreakerTransportError` are the breaker's own
exception types. They stay inside the SDK, so neither
`except NullRunError` nor `except BreakerTransportError` in your code
sees one.

One breaker error does reach you, and it happens at start-up rather than
during a run: an API URL on plain HTTP against a host that is not
localhost raises `InsecureTransportError`.

## What it does not do

The breaker does not sit on the gate path. It guards the event flush,
not the policy decision. A protected call is never blocked by it.

When the gateway cannot be reached, the gate path fails closed on its
own. A network failure raises `NullRunBlockedException` with `NR-B001`,
a gateway 5xx raises `NullRunBlockedException` with `NR-B002`, and a
rejected key raises `NullRunAuthError` with `NR-A003`. The protected body
does not run in any of the three cases. See
[Policies → Fail closed](policies.md#fail-closed).

The gateway keeps a per-workflow breaker of its own. When breaker
enforcement is on, an open workflow breaker refuses the call with HTTP
403 `CIRCUIT_BREAKER_TRIPPED`, which the SDK raises as
`NullRunBlockedException`.

The breaker never relaxes enforcement. A tool block, a budget refusal
and a rate-limit refusal are answers from the gateway, and the SDK
raises them whatever state the breaker is in.

## See also

- [Policies](policies.md) — the rules the gate enforces
- [Error handling](error-handling.md) — how a refusal reaches your code
- [Troubleshooting](../troubleshooting.md) — common "why is my agent
  blocked?" questions
