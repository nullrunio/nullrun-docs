---
title: Configuration
description: Every NullRun SDK environment variable, transport option, and fail-CLOSED guard documented with safe defaults.
---

# Configuration

NullRun reads configuration from environment variables. `nullrun.init()`
only needs the API key — everything else has sensible defaults.

Variables are read by the Python SDK process. The gateway is operated
by the NullRun team and exposes no user-facing runtime flags.

## SDK env vars

Read by `nullrun.init` and the SDK transport. None of these affect the
gateway.

| Variable | Default | Description |
| --- | --- | --- |
| `NULLRUN_API_KEY` | unset (required) | API key from the NullRun dashboard (`nr_live_...`). Missing at `init()` raises `NullRunAuthenticationError` (NR-C001). |
| `NULLRUN_API_URL` | `https://api.nullrun.io` | Gateway REST base URL. The WebSocket control plane URL is derived from this as `wss://<api-host>/ws/control/{org_id}` — `{org_id}` is the `organization_id` returned by `POST /api/v1/auth/verify`, and is **not** a separate env var. |
| `NULLRUN_SECRET_KEY` | unset | HMAC-SHA256 signing secret. The SDK signs every request automatically when this is set. |
| `NULLRUN_ENV` | unset | Environment tag (`production` / `staging` / ...). |
| `NULLRUN_APPROVAL_TIMEOUT_SECONDS` | `300` | SDK-side wait for the `approval_resolved` WS push before fail-CLOSED kill. |
| `NULLRUN_REQUEST_TIMEOUT` | `30` | HTTP request timeout in seconds. |
| `NULLRUN_TRANSPORT` | `ws` | Control-plane transport mode (`ws` or `http`). |
| `NULLRUN_GATE_CACHE_DISABLE` | unset | `=1` disables the SDK's local gate cache (forces a fresh gate evaluation on every `@protect` call). |
| `NULLRUN_TLS_CLIENT_CERT` / `NULLRUN_TLS_CLIENT_KEY` / `NULLRUN_TLS_CA_CERT` | unset | Optional mTLS material for the SDK-to-gateway connection. |
| `NULLRUN_MAX_RESPONSE_BYTES` | library default | Cap on captured LLM response body size for span metadata. |

## Developer and CI overrides

!!! danger "Production-safe default: do NOT set these in production traffic"
    The variables below override the gate's safety defaults. They
    exist for local SDK development and CI only. Exporting them in
    a production environment silently disables protection — your
    agent will run un-gated.

| Variable | Effect | When to use |
| --- | --- | --- |
| `NULLRUN_SKIP_BUDGET_CHECK=1` | Fully bypasses the gate on every `@protect` call in the process. **For local SDK development and CI only** — do not export in production environments. Production with this flag set silently skips every policy check. | Local SDK experiments, integration tests where you want to verify business logic without gate noise. |
| `NULLRUN_ALLOW_SKIP_BUDGET_CHECK=1` | Acknowledges the previous flag in CI logs so an audit reviewer can see the bypass was deliberate. Has no effect by itself; safe to set alongside the previous flag in CI. | CI pipelines that intentionally skip the gate. |
| `NULLRUN_SENSITIVE_FAIL_OPEN=1` | Returns a permissive result instead of failing-CLOSED when a sensitive-tool transport error blocks the gate call. | Legacy environments without a working transport for sensitive-tool lookups — modern installs should leave this unset. |

If a CI test "passes only with `NULLRUN_SKIP_BUDGET_CHECK=1`" that's a
signal the gate is blocking what it should not — fix the gate, not
the bypass.

## Server-side configuration

NullRun runs as a managed service; the gateway is operated by the
NullRun team and exposes no user-facing runtime flags.

## Behaviour

The HTTP request timeout is configurable via `NULLRUN_REQUEST_TIMEOUT`
(default `30`s).

The control-plane transport (WS push vs. HTTP polling fallback) is
configured by `NULLRUN_TRANSPORT` (default `ws`). The default is WS
push with HTTP polling fallback when the WS connection drops more than
10 times in a row.

HMAC signature window (`NULLRUN_HMAC_MAX_AGE_SECS`, default `300`s) is
a server-side setting. The SDK signs every request automatically when
`NULLRUN_SECRET_KEY` is set.

## See also

- [HTTP API](../reference/http-api.md)
- [Control plane](../concepts/control-plane.md)
- [Circuit breaker](../concepts/circuit-breaker.md)
