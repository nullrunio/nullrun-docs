---
title: Configuration
description: Every NullRun SDK environment variable, transport option, and fail-CLOSED guard documented with safe defaults.
---

# Configuration

NullRun reads configuration from environment variables. The runtime
is created lazily on the first protected execution. Only
`NULLRUN_API_KEY` is required; everything else has sensible defaults.

Variables are read by the Python SDK process on the first `@protect`
call. The gateway is operated by the NullRun team and exposes no
user-facing runtime flags.

## SDK env vars

Read by the SDK transport when the runtime is created on the first
`@protect` call. None of these affect the gateway.

| Variable | Default | Description |
| --- | --- | --- |
| `NULLRUN_API_KEY` | unset (required) | API key from the NullRun dashboard (`nr_live_...`). Missing at the first `@protect` call raises `NullRunConfigError`. |
| `NULLRUN_SECRET_KEY` | unset | HMAC-SHA256 signing secret returned by `POST /auth/verify`. The SDK signs every request automatically when this is set. |
| `NULLRUN_API_URL` | `https://api.nullrun.io` | Gateway REST base URL — only override this when pointing at a regional or staging cluster. |

## Developer and CI overrides

!!! danger "Production-safe default: do NOT set these in production traffic"
    The variables below override the gate's safety defaults. They
    exist for local SDK development and CI only. Exporting them in
    a production environment silently disables protection — your
    agent will run un-gated.

| Variable | Effect | When to use |
| --- | --- | --- |
| `NULLRUN_SKIP_BUDGET_CHECK=1` | Fully bypasses the gate on every `@protect` call in the process. **For local SDK development and CI only** — do not export in production environments. Production with this flag set silently skips every policy check. | Local SDK experiments, integration tests where you want to verify business logic without gate noise. |
| `NULLRUN_SENSITIVE_FAIL_OPEN=1` | Returns a permissive result instead of failing-CLOSED when a sensitive-tool transport error blocks the gate call. | Environments without a working transport for sensitive-tool lookups — modern installs should leave this unset. |

If a CI test "passes only with `NULLRUN_SKIP_BUDGET_CHECK=1`" that's a
signal the gate is blocking what it should not — fix the gate, not
the bypass.

## Server-side configuration

NullRun runs as a managed service; the gateway is operated by the
NullRun team and exposes no user-facing runtime flags.

## Behaviour

The control-plane transport is WebSocket push with an HTTP polling
fallback that takes over when the WS connection drops repeatedly.

## See also

- [HTTP API](../reference/http-api.md)
- [Control plane](../concepts/control-plane.md)
- [Circuit breaker](../concepts/circuit-breaker.md)
