---
title: CI/CD integration
description: Run a synthetic load against a pre-prod gateway in CI, and fail the build when the gate refuses.
maturity: stable
---

# CI / CD integration

Wire NullRun into the build so a policy mistake is caught before it
reaches production.

The check drives the real SDK against a real gateway with synthetic
token counts. No LLM provider is called, so the job costs nothing and
spends no provider tokens.

## The load tool

The examples repo ships a CLI for this:
[`synthetic_sdk_load.py`](https://github.com/nullrunio/nullrun-examples/blob/master/tools/synthetic_sdk_load.py).

It runs the public SDK path. Each call sends a gate request, then a
tracking request with random token counts.

| Flag | Meaning |
|---|---|
| `--interval` | Seconds between call launches |
| `--duration` | Duration cap in seconds |
| `--requests` | Request cap. `0` uses the duration cap only |
| `--workers` | Maximum concurrent calls |
| `--model` | Model name reported for the synthetic calls |
| `--min-tokens`, `--max-tokens` | Range the random token counts fall in |
| `--seed` | Seed for the random generator |
| `--dry-run` | Schedule locally without sending anything |
| `--yes` | Skip the confirmation prompt |

Exit code:

| Code | Meaning |
|---|---|
| `0` | Every call succeeded |
| `1` | At least one call failed |
| `2` | The confirmation was declined |

## GitHub Actions

```yaml title=".github/workflows/pre-prod.yml"
name: pre-prod-validation

on:
  pull_request:
    branches: [master]

jobs:
  nullrun-smoke:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    env:
      NULLRUN_API_URL: ${{ secrets.NULLRUN_PRE_PROD_URL }}
      NULLRUN_API_KEY: ${{ secrets.NULLRUN_PRE_PROD_KEY }}
    steps:
      - uses: actions/checkout@v4

      - name: Install the SDK and the load tool
        run: |
          git clone --depth 1 https://github.com/nullrunio/nullrun-examples.git
          pip install nullrun

      - name: 1. Health check
        run: curl -fs "${NULLRUN_API_URL}/health/live"

      - name: 2. Capabilities probe
        run: |
          curl -fs "${NULLRUN_API_URL}/api/v1/capabilities" | python -c '
          import json, sys
          payload = json.load(sys.stdin)
          caps = payload.get("capabilities") or {}
          flags = (
              "server_minted_execution_id",
              "per_execution_reservations",
              "heartbeat_time_based",
          )
          missing = [f for f in flags if not caps.get(f)]
          assert not missing, "gateway is not ready: " + ", ".join(missing)
          lo = payload["min_protocol_version"]
          hi = payload["max_protocol_version"]
          assert lo <= 4 <= hi, f"gateway accepts protocol {lo}..{hi}, the SDK sends 4"
          '

      - name: 3. Synthetic load
        working-directory: nullrun-examples
        run: |
          set -euo pipefail
          python tools/synthetic_sdk_load.py \
            --interval 0.05 \
            --workers 10 \
            --requests 200 \
            --model gpt-4o-mini \
            --yes
```

`set -euo pipefail` makes the step fail on the first error. The exit
code of the load tool is the CI gate.

## The checks

**The health check** confirms the gateway answers. It reads no
organization data, so it needs no key.

**The capabilities probe** confirms the gateway speaks the wire
contract the SDK needs. Three flags must be true:
`server_minted_execution_id`, `per_execution_reservations`, and
`heartbeat_time_based`. The endpoint sits outside the protocol-gated
routes, so it answers without the protocol header.

The SDK sends `X-NULLRUN-PROTOCOL: 4`. The gateway advertises the
range it accepts as `min_protocol_version` and `max_protocol_version`.

**The synthetic load** runs the gate for real. It catches:

- a budget cap that is too tight for the traffic
- a rate limit that refuses the traffic
- a key that is missing, revoked, or bound to another organization
- a policy that refuses every call

## What the load does not catch

- **Real spend.** The token counts are random. Use a staging workflow
  with a small cap for a cost estimate.
- **Pricing for a model.** Check the cost view in the dashboard after
  one real call.
- **Kill and pause.** The synthetic load does not exercise the
  control-plane paths. Trigger them by hand during a release
  checklist.
- **Your tool names.** The load tool gates a function of its own. It
  tells you the tool policy refuses calls, not which of your tool
  names it refuses.

## The manual step

An approval flow needs a human to click **Approve**. Run it by hand on
every release candidate. See
[Human approval](../concepts/human-approval.md).

## Common failures

| Symptom | Meaning | Fix |
|---|---|---|
| The tool exits `1` and prints a configuration report | `NULLRUN_API_KEY` is missing | Add the key to the job secrets |
| Every call raises a budget refusal | The pre-prod cap is too tight for the load | Raise the cap on the pre-prod workflow |
| Every call raises a rate-limit refusal | The rate limit is below the load rate | Raise the rate limit on the pre-prod workflow |
| The health check fails to connect | `NULLRUN_API_URL` is wrong | Point it at the pre-prod gateway |
| The capabilities probe reports a missing flag | The gateway is older than the SDK expects | Upgrade the gateway before the deploy |

## See also

- [Troubleshooting](../troubleshooting.md) — how to read SDK logs
- [Configuration → env vars](../getting-started/configuration.md)
- [HTTP API → Capabilities](../reference/http-api.md#capabilities)
