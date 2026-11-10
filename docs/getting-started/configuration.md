---
title: Configuration
description: Every NullRun SDK environment variable, what it controls, its default, and the two development bypasses the SDK refuses in production.
maturity: stable
---

# Configuration

The Python SDK reads its settings from environment variables. Only `NULLRUN_API_KEY` is required. The gateway is operated by the NullRun team and exposes no user-facing runtime flags.

## Connection

| Variable | Purpose | Default |
| --- | --- | --- |
| `NULLRUN_API_KEY` | API key from the control center (`nr_live_...`). The SDK signs every gateway request with it. | unset — required |
| `NULLRUN_SECRET_KEY` | Signing secret for that key. The SDK fetches it from `POST /api/v1/auth/verify` when this variable is unset. | unset |
| `NULLRUN_API_URL` | Base URL of the gateway. Point it at a self-hosted gateway only if you run one. | `https://api.nullrun.io` |
| `NULLRUN_ENV` | Deployment label. `production` or `prod` marks the process as production. | unset |
| `NULLRUN_REQUEST_TIMEOUT` | Seconds the SDK waits for one gateway request. | `30` |

The SDK treats a process as production when `NULLRUN_ENV` is `production` or `prod`, or when the gateway URL is `api.nullrun.io`. A loopback host is never production, whatever `NULLRUN_ENV` says. Production arms the guards on the development bypasses below.

## Gate and approvals

| Variable | Purpose | Default |
| --- | --- | --- |
| `NULLRUN_TRANSPORT` | Control-plane transport: `ws` for WebSocket push, `http` for polling. | `ws` |
| `NULLRUN_APPROVAL_TIMEOUT_SECONDS` | Seconds the SDK waits for a human approval decision. It is the fallback when the gateway sends no timeout of its own. | `300` |
| `NULLRUN_V3_TRACK_DISABLE` | Set to `1` to send every tracked event through the batch path instead of the single-event path. Use it on a gateway that does not settle per-execution reservations. | unset |

## Event delivery

| Variable | Purpose | Default |
| --- | --- | --- |
| `NULLRUN_BATCH_SIZE` | Number of tracked events the SDK sends per flush. | `50` |
| `NULLRUN_FLUSH_INTERVAL_MS` | Milliseconds between flushes of tracked events. | `5000` |
| `NULLRUN_MAX_BATCH_ATTEMPTS` | How many times the SDK sends one batch before it moves that batch to the dead-letter file. | `10` |
| `NULLRUN_MAX_BISECT_REQUESTS` | How many requests the SDK may send while it splits a batch the gateway rejected. | `64` |
| `NULLRUN_RETRY_AFTER_CEILING` | Seconds the SDK waits when the gateway answers `429` with a `Retry-After` header. A `Retry-After` above this ceiling is not retried in the current cycle. | `60` |
| `NULLRUN_MAX_RESPONSE_BYTES` | Largest HTTP response body the SDK reads for token counting. A bigger body is delivered to your code but not counted. | `16777216` (16 MiB) |

## Write-ahead log

The SDK keeps events it could not deliver in a write-ahead log on disk. The log holds the events the gateway has not accepted yet, so a crash or a network outage does not lose spend that already happened.

| Variable | Purpose | Default |
| --- | --- | --- |
| `NULLRUN_WAL_PATH` | Path of the write-ahead log. Give every runtime its own path. | `<tempdir>/nullrun-<user>-<key-digest>.wal` |
| `NULLRUN_WAL_MAX_BYTES` | Size at which the SDK rotates the write-ahead log. | `67108864` (64 MiB) |
| `NULLRUN_WAL_LOCK_TIMEOUT_MS` | Milliseconds the SDK waits for the write-ahead log lock before it gives up. | `5000` |
| `NULLRUN_DLQ_MAX_BYTES` | Size at which the SDK stops adding to the dead-letter file. | `67108864` (64 MiB) |
| `NULLRUN_DLQ_HOLDOVER_MAX_EVENTS` | Number of dead-letter entries the SDK keeps in memory as an index. The file itself keeps every row. | `10000` |

The default write-ahead log path carries a digest of the API key, not the key itself. Two API keys on one machine never share a file.

## Edge node

| Variable | Purpose | Default |
| --- | --- | --- |
| `NULLRUN_EDGE_URL` | Base URL of an edge node that enforces the gate next to the agent. | unset |
| `NULLRUN_EDGE_LEASE_ID` | Lease the edge node uses for this runtime. Required when `NULLRUN_EDGE_URL` is set. | unset |
| `NULLRUN_EDGE_TOKEN` | Token the edge node authenticates with. Required when `NULLRUN_EDGE_URL` is set. | unset |
| `NULLRUN_EDGE_TIMEOUT_SECONDS` | Seconds the SDK waits for one edge node request. | `2` |
| `NULLRUN_EDGE_MAX_RETRIES` | How many times the SDK retries a failed edge node request. | `2` |

`NULLRUN_API_KEY` is required as well when `NULLRUN_EDGE_URL` is set. The edge node checks the caller's key against the fingerprint inside the grant.

## TLS

| Variable | Purpose | Default |
| --- | --- | --- |
| `NULLRUN_TLS_CA_CERT` | Path to a custom CA certificate the SDK trusts when it reaches the gateway. | unset |
| `NULLRUN_TLS_CLIENT_CERT` | Path to a client certificate the SDK presents to the gateway. | unset |
| `NULLRUN_TLS_CLIENT_KEY` | Path to the key of that client certificate. | unset |

## Malformed values

A value that is not a number is ignored. `NULLRUN_BATCH_SIZE`,
`NULLRUN_FLUSH_INTERVAL_MS`, `NULLRUN_EDGE_TIMEOUT_SECONDS`, and
`NULLRUN_EDGE_MAX_RETRIES` log a warning that names the variable.

Three variables have no fallback. `NULLRUN_MAX_RESPONSE_BYTES`,
`NULLRUN_MAX_BATCH_ATTEMPTS`, and `NULLRUN_MAX_BISECT_REQUESTS` must be
whole numbers. A non-numeric value raises `ValueError` and stops
`nullrun.init()`.

## Development and test bypasses

!!! danger "A production deployment must not set these"
    The two variables below switch off a safety check. They exist for local development and for test suites. A production deployment must not set them, and a test that only passes with them set is a defect in the gate, not in the test.

| Variable | Effect |
| --- | --- |
| `NULLRUN_SKIP_BUDGET_CHECK=1` | Skips the budget pre-flight on every protected call in the process. The call is still tracked and billed, but nothing is reserved against the budget. |
| `NULLRUN_SENSITIVE_FAIL_OPEN=1` | Lets a protected tool run when the policy engine cannot be reached. Only tools the operator classified as fail-open-allowed are affected. The set of classified tools is empty until you call `register_fail_open_tools` on the runtime, so the switch alone opens nothing. |

Each one needs a second variable that acknowledges the risk:

| Variable | Effect |
| --- | --- |
| `NULLRUN_ALLOW_SKIP_BUDGET_CHECK=1` | Acknowledges `NULLRUN_SKIP_BUDGET_CHECK=1` in production. |
| `NULLRUN_ALLOW_SENSITIVE_FAIL_OPEN=1` | Acknowledges `NULLRUN_SENSITIVE_FAIL_OPEN=1` in production. |

The SDK refuses a bypass that is armed in production without its acknowledgement. `NULLRUN_SKIP_BUDGET_CHECK=1` raises `NullRunInfrastructureError` with the code `NR-S001`. `NULLRUN_SENSITIVE_FAIL_OPEN=1` is ignored, and the tools stay fail-closed.

## Behaviour

The control plane carries workflow state — kill, pause, resume. The SDK receives it over a WebSocket push channel. It falls back to polling the gateway every second when the WebSocket endpoint is blocked, when the `websockets` package is not installed, or when `NULLRUN_TRANSPORT=http` selects the poller.

The edge settings change where the gate runs. With `NULLRUN_EDGE_URL` set, the gate request goes to the edge node instead of the cloud. Cost events still go to the cloud. An unreachable edge node refuses the call. The SDK does not fall back to the cloud, because a silent fallback would let the agent keep spending with no grant in force.

`NULLRUN_USE_GRPC` is reserved. Setting it makes `init()` raise a `RuntimeError`, because the gRPC transport is not implemented.

## See also

- [HTTP API](../reference/http-api.md)
- [Install → optional extras](install.md#optional-extras)
- [Concepts → Control plane](../concepts/control-plane.md)
- [Concepts → Circuit breaker](../concepts/circuit-breaker.md)
