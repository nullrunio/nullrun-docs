---
title: Circuit breaker
maturity: stable
description: The SDK-side circuit breaker — it opens after repeated transport failures, short-circuits calls while open, and recovers after a cooldown.
---

# Circuit breaker

The SDK ships a client-side circuit breaker. It sits in the transport
layer and watches the calls the SDK makes to the gateway. After a run
of transport failures it opens and stops sending, so an unreachable
gateway does not turn into a hang. It closes again after a cooldown.

A policy refusal and a breaker trip are different things:

- A **policy refusal** is the gateway answering "no". The gate
  evaluated your rules and blocked the call.
- A **breaker trip** is the SDK noticing that the gateway is not
  answering at all.

## States

| State | What happens |
|---|---|
| **Closed** | Calls go out normally. A transport failure raises the failure count. A success resets it. |
| **Open** | Calls short-circuit. The SDK raises `BreakerTransportError` instead of waiting on the network. |
| **Half-open** | The breaker lets one probe through. A success closes it. Another failure opens it again. |

## When it opens

The breaker opens after a run of consecutive transport failures: a
timeout, a refused connection, a 5xx. The threshold on the SDK's
event-flush path is the failed-flush limit, 10 by default. The
half-open probe waits 30 seconds.

While the breaker is open the SDK keeps the pending work on disk and
retries it on a later flush. No record is dropped, and the agent keeps
running.

## What it raises

`BreakerTransportError` extends `BreakerError`. It is not a
`NullRunError`, so `except NullRunError` does not catch it:

```python
from nullrun import BreakerError, BreakerTransportError

try:
    run_agent("...")
except BreakerTransportError:
    # The gateway was not answering.
    # The SDK is protecting itself, not enforcing a rule.
    ...
```

A breaker-open transport failure on the `@protect` gate surfaces as a
block with `error_code = "NR-B005"`, and the protected body does not
run.

## What it does not do

The breaker never relaxes enforcement. A tool block, a budget refusal
and a rate-limit refusal are answers from the gateway, and the SDK
raises them whatever state the breaker is in. When the gateway cannot
be reached at all, the enforcement path refuses — see
[Policies → Fail closed](policies.md#fail-closed).

## See also

- [Policies](policies.md) — the rules the gate enforces
- [Error handling](error-handling.md) — how a refusal reaches your code
- [Troubleshooting](../troubleshooting.md) — common "why is my agent
  blocked?" questions
