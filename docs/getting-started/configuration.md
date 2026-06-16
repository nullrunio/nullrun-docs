# Configuration

NullRun reads configuration from environment variables. `init()` only
needs the API key — everything else has sensible defaults.

## Required

| Variable | Description |
| --- | --- |
| `NULLRUN_API_KEY` | API key from the NullRun dashboard |

## Optional

| Variable | Default | Description |
| --- | --- | --- |
| `NULLRUN_API_URL` | `https://api.nullrun.io` | Gateway base URL |
| `NULLRUN_TIMEOUT` | `30` | HTTP request timeout (seconds) |
| `NULLRUN_BATCH_SIZE` | `100` | Event batch size |
| `NULLRUN_FLUSH_INTERVAL_MS` | `5000` | Event flush interval (ms) |
| `NULLRUN_LOG_LEVEL` | `INFO` | One of `DEBUG` / `INFO` / `WARNING` / `ERROR` |

## Test / dev opt-outs

| Variable | When to use | Risk |
| --- | --- | --- |
| `NULLRUN_SKIP_BUDGET_CHECK=1` | Skip the pre-flight `/check` (test only) | Agent may overspend before `/track` sees it |
| `NULLRUN_SENSITIVE_FAIL_OPEN=1` | Sensitive tools allow when gateway is down (test only) | Sensitive tool runs without policy check |

Both opt-outs **emit a `RuntimeWarning`** at import time so they can't
slip into production unnoticed.

## gRPC transport (experimental — FROZEN)

The gRPC transport is intentionally frozen and must not be enabled in
production. See the SDK README for the activation checklist (TLS → auth
→ proto extensions → cost pipeline parity → tests).

## See also

- [How-to → Self-host](../how-to/self-host.md) (planned)
- [Reference → Environment variables](../reference/env-vars.md) (planned)
