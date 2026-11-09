---
title: Configuration
description: Every NullRun SDK environment variable, its purpose, and its default.
maturity: stable
---

# Configuration

The Python SDK reads its settings from environment variables. Only `NULLRUN_API_KEY` is required. The gateway is operated by the NullRun team and exposes no user-facing runtime flags.

## Settings

| Variable | Purpose | Default |
| --- | --- | --- |
| `NULLRUN_API_KEY` | API key from the dashboard (`nr_live_...`). The SDK signs every gateway request with it. | unset — required |
| `NULLRUN_SECRET_KEY` | Signing secret for that key. The SDK fetches it from `POST /api/v1/auth/verify` when this variable is unset. | unset |
| `NULLRUN_API_URL` | Base URL of the gateway. Point it at a self-hosted gateway only if you run one. | `https://api.nullrun.io` |
| `NULLRUN_ENV` | Deployment label. The value `production` or `prod` marks the process as production, which arms the guards on the development bypasses below. | unset |
| `NULLRUN_REQUEST_TIMEOUT` | Seconds the SDK waits for one gateway request. | `30` |
| `NULLRUN_APPROVAL_TIMEOUT_SECONDS` | Seconds the SDK waits for a human approval decision. It is the fallback when the gateway sends no timeout of its own. | `300` |
| `NULLRUN_TRANSPORT` | Control-plane transport: `ws` for WebSocket push, `http` for polling. | `ws` |
| `NULLRUN_BATCH_SIZE` | Number of tracked events the SDK sends per flush. | `50` |
| `NULLRUN_FLUSH_INTERVAL_MS` | Milliseconds between flushes of tracked events. | `5000` |
| `NULLRUN_WAL_PATH` | Path of the write-ahead log that holds events that could not be delivered yet. Give every runtime its own path. | `<tempdir>/nullrun-<user>-<key>.wal` |
| `NULLRUN_EDGE_URL` | Base URL of an edge node that enforces the gate next to the agent. | unset |
| `NULLRUN_EDGE_LEASE_ID` | Lease the edge node uses for this runtime. Required when `NULLRUN_EDGE_URL` is set. | unset |
| `NULLRUN_EDGE_TOKEN` | Token the edge node authenticates with. | unset |

A value that is not a number is ignored, and the SDK logs a warning naming the variable.

## Development and test bypasses

!!! danger "A production deployment must not set these"
    The two variables below switch off a safety check. They exist for local development and for test suites. A production deployment must not set them, and a test that only passes with them set is a defect in the gate, not in the test.

| Variable | Effect |
| --- | --- |
| `NULLRUN_SKIP_BUDGET_CHECK=1` | Skips the budget pre-flight on every protected call in the process. |
| `NULLRUN_SENSITIVE_FAIL_OPEN=1` | Lets a sensitive tool run when the policy engine cannot be reached. Only tools the operator classified as fail-open-allowed are affected. |

Each one needs a second variable that acknowledges the risk:

| Variable | Effect |
| --- | --- |
| `NULLRUN_ALLOW_SKIP_BUDGET_CHECK=1` | Acknowledges `NULLRUN_SKIP_BUDGET_CHECK=1` in production. |
| `NULLRUN_ALLOW_SENSITIVE_FAIL_OPEN=1` | Acknowledges `NULLRUN_SENSITIVE_FAIL_OPEN=1` in production. |

The SDK refuses a bypass that is armed in production without its acknowledgement. It logs the refusal and continues to enforce.

## Behaviour

The control plane carries workflow state — kill, pause, resume. The SDK receives it over a WebSocket push channel. It falls back to polling the gateway every second when the WebSocket endpoint is blocked, when the `websockets` package is not installed, or when `NULLRUN_TRANSPORT=http` selects the poller.

The edge settings change where the gate runs. With `NULLRUN_EDGE_URL` set, the gate request goes to the edge node instead of the cloud. Cost events still go to the cloud.

## See also

- [HTTP API](../reference/http-api.md)
- [Install → optional extras](install.md#optional-extras)
- [Concepts → Control plane](../concepts/control-plane.md)
- [Concepts → Circuit breaker](../concepts/circuit-breaker.md)
