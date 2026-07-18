# Run multiple agents (multi-key / multi-process)

NullRun's `init()` binds one API key to one process. The SDK
intentionally shuts down any prior runtime on a second `init()` call
so you cannot accidentally keep stale daemon threads pointing at a
different key.

For everything beyond a single one-shot script, run **one process per
key**. This page shows the three patterns that cover real workloads.

## Pattern 1 — multiple agents on one host (systemd / supervisor)

The simplest production deployment. Each workflow gets its own
service unit, its own env var, its own log stream.

```ini title="/etc/systemd/system/nullrun-prod-bot.service"
[Service]
Environment="NULLRUN_API_KEY=***"
Environment="NULLRUN_API_URL=https://api.nullrun.io"
ExecStart=/usr/bin/python /opt/nullrun/prod_bot.py
Restart=on-failure
User=nullrun

[Install]
WantedBy=multi-user.target
```

```ini title="/etc/systemd/system/nullrun-staging-bot.service"
[Service]
Environment="NULLRUN_API_KEY=***"
Environment="NULLRUN_API_URL=https://api.nullrun.io"
ExecStart=/usr/bin/python /opt/nullrun/staging_bot.py
Restart=on-failure
User=nullrun

[Install]
WantedBy=multi-user.target
```

```bash title="shell"
sudo systemctl daemon-reload
sudo systemctl enable --now nullrun-prod-bot nullrun-staging-bot
```

Each unit talks to the gateway with its own key, so the dashboard's
**Workflows** view shows separate per-workflow spend, kill/pause
works independently, and you can restart one without affecting the
other.

For Docker Compose the same shape is `environment:` per service:

```yaml title="docker-compose.yml"
services:
  prod-bot:
    image: yourorg/agent:latest
    environment:
      NULLRUN_API_KEY: ***
      NULLRUN_API_URL: https://api.nullrun.io
  staging-bot:
    image: yourorg/agent:latest
    environment:
      NULLRUN_API_KEY: ***
      NULLRUN_API_URL: https://api.nullrun.io
```

For Kubernetes, mount the key as a `Secret` and reference it in each
Deployment's `envFrom`.

## Pattern 2 — fan-out inside one container (multiprocessing.Pool)

When you have one entrypoint but N workflows to run, use
`multiprocessing.Pool` so each child inherits its own SDK singleton
and its own key:

```python title="fanout.py"
import multiprocessing as mp
import os
import nullrun
from nullrun import init_or_die, protect


def _agent_main(key: str, prompt: str) -> str:
    # Each child process initializes its own runtime with its own key.
    init_or_die(api_key=key)

    @protect
    def step(p: str) -> str:
        return your_llm_call(p)

    return step(prompt)


def fan_out(jobs: list[tuple[str, str]]) -> list[str]:
    # jobs is [(key, prompt), ...] — one key per workflow.
    with mp.Pool(processes=len(jobs)) as pool:
        async_results = [
            pool.apply_async(_agent_main, args=(k, p))
            for k, p in jobs
        ]
        return [r.get(timeout=120) for r in async_results]
```

The pool's `fork` start method (default on Linux) gives each child its
own copy of the SDK state, so each `init()` runs cleanly with no
shutdown collisions. **Do not** call `init()` once at the parent and
share the runtime across children — that's the multi-key-in-one-process
anti-pattern and you'll get shutdown warnings the moment the first
child finishes.

For `spawn` (default on macOS / Windows) the rule is the same — each
child is a fresh interpreter and runs its own `init()` independently.

## Pattern 3 — one entrypoint, multiple keys, hard process boundary

If you have one CLI / API server that needs to handle requests for
many workflows, route at the **process level** rather than the
**function level**:

```python title="router.py"
import os
import subprocess


def run_workflow(key: str, prompt: str) -> str:
    """Spawn a fresh subprocess for each request. Each one is its own
    SDK singleton, so multi-key isolation is automatic."""
    result = subprocess.run(
        ["python", "agent.py", prompt],
        env={**os.environ, "NULLRUN_API_KEY": key},
        capture_output=True,
        text=True,
        timeout=120,
    )
    check=True,
    timeout=120,
    )
    return result.stdout
```

The subprocess startup cost (~150 ms for `init()` + WebSocket connect)
is the price for clean isolation. For high-throughput paths, see
Pattern 2 — multiprocessing keeps workers warm in a pool.

## What doesn't work

Calling `init()` more than once in the **same** process. The SDK
detects this and shuts down the prior runtime:

```python title="broken_multi_key.py"
import nullrun
from nullrun import init

init(api_key="nr_live_aaa")   # first runtime lives here
init(api_key="nr_live_bbb")   # ← first runtime is shut down here
                               #   (with a WARNING log); only the second one
                               #   survives. Subsequent /gate and /track
                               #   calls go out under nr_live_bbb.
```

If you actually need multiple keys to coexist in one process — for
example, a single FastAPI process that serves many customers each
with their own NullRun key — you have to keep the keys **server-side**
and route per-request, with one SDK subprocess or one dedicated
process per customer. There is no in-process SDK API for that.

## What if I want a single dashboard view across all my processes?

You don't need anything special — the dashboard already aggregates per
workflow across all processes holding that workflow's key. As long as
every subprocess binds to the **same** workflow (i.e. uses the same
key), all their `/gate` and `/track` calls land on the same workflow
record in the backend.

The case where this **doesn't** hold is the "many workflows, one
process" anti-pattern above: each `init()` call swaps the active key
but the prior workflow's events have already gone to the prior key's
workflow.

## See also

- [Configuration → env vars](../getting-started/configuration.md)
- [Concepts → API keys](../concepts/api-keys.md) — workflow-scoping
  and the `1:1` binding between key and workflow
- [Concepts → Workflow context](../concepts/workflow.md)
