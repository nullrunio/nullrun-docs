# Run multiple agents (multi-key / multi-process)

NullRun's `init()` is intended to be called **once per process**.
The SDK's runtime is a process-scoped singleton — transport pool,
WebSocket subscription, and event batch buffer. If you call `init()`
twice in the same process, behaviour depends on the runtime
implementation; the supported pattern is one `init()` per process
and one process per workflow key.

For everything beyond a single one-shot script, run **one process per
key**. This page shows the three patterns that cover real workloads.

## Pattern 1 — multiple agents on one host (one process per key)

The simplest production deployment. Each workflow gets its own
process, its own env var, its own log stream. Common supervisors
include systemd, Docker Compose, and Kubernetes — pick whichever
fits the platform. The rule is the same regardless of supervisor:
each process gets its own `NULLRUN_API_KEY` so the dashboard's
**Workflows** view shows separate per-workflow spend, kill/pause
works independently, and you can restart one without affecting the
other.

## Pattern 2 — fan-out inside one container (multiprocessing.Pool)

When you have one entrypoint but N workflows to run, use
`multiprocessing.Pool` so each child initializes its own SDK runtime
and its own key:

```python title="fanout.py"
import multiprocessing as mp
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

Each child gets its own copy of the SDK state, so each `init()` runs
cleanly with no shutdown collisions. **Do not** call `init()` once at
the parent and share the runtime across children — that's the
multi-key-in-one-process anti-pattern and you'll get shutdown warnings
the moment the first child finishes.

Pick the pool start method that matches your platform (see the
`multiprocessing` docs). The rule is the same regardless: each child
is a fresh interpreter and runs its own `init()` independently.

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
        check=True,
    )
    return result.stdout
```

The subprocess startup cost (~150 ms for `init()` + WebSocket connect)
is the price for clean isolation. For high-throughput paths, see
Pattern 2 — multiprocessing keeps workers warm in a pool.

## What doesn't work

Calling `init()` more than once in the same process is not a
supported pattern. The runtime singleton is process-scoped, and
mixing multiple keys in one process leads to interleaved events
on the wrong workflow. The supported alternative is one process per
key (Pattern 1) or one subprocess per request (Pattern 3).

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
