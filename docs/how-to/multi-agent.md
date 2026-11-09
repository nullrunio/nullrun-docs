---
title: Several agents on one host
description: Run several agents on one host. Each API key binds to one workflow, and each process holds one runtime and one key at a time.
maturity: stable
---

# Run several agents on one host

Two rules shape every deployment:

1. An API key binds to one workflow.
2. The SDK holds one runtime per process.

So N workflows on one host means N processes. This page shows the three
patterns that cover real deployments.

For sub-agents that share one workflow inside one process, see
[Multi-agent orchestration](multi-agent-orchestration.md).

## Pattern 1 — one process per key

Each workflow gets its own process, its own environment variable, and
its own log stream. Any supervisor works: systemd, Docker Compose, or
Kubernetes.

The rule does not change with the supervisor. Give each process its own
`NULLRUN_API_KEY`:

```bash title="service.env"
NULLRUN_API_KEY=nr_live_replace_me
```

The control center then shows separate spend per workflow, kill and pause
work independently, and you can restart one without touching the
others.

## Pattern 2 — fan out inside one container

Use a process pool when one entrypoint has N workflows to run. Each
child builds its own runtime from its own key.

```python title="fanout.py"
import multiprocessing as mp
import os

from nullrun import protect


def call_model(text: str) -> str:
    """Your model call goes here."""
    return text


def _run_one(job: tuple[str, str]) -> str:
    key, prompt = job
    # The runtime is created lazily on the first @protect call, so the
    # key has to be in the environment before that happens.
    os.environ["NULLRUN_API_KEY"] = key

    @protect
    def step(text: str) -> str:
        return call_model(text)

    return step(prompt)


def fan_out(jobs: list[tuple[str, str]]) -> list[str]:
    # "spawn" gives every child a fresh interpreter and a fresh runtime.
    ctx = mp.get_context("spawn")
    with ctx.Pool(processes=len(jobs)) as pool:
        return pool.map(_run_one, jobs)
```

Use the `spawn` start method. The `fork` method copies the parent's
memory into the child. If the parent already created a runtime, the
child inherits it and reports to the parent's workflow with the parent's
key.

## Pattern 3 — one subprocess per request

Route at the process level when one CLI or API server handles requests
for many workflows.

```python title="router.py"
import os
import subprocess


def run_workflow(key: str, prompt: str) -> str:
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

Each subprocess is its own interpreter with its own runtime, so the
isolation is automatic. The price is process startup on every request.
For a steady stream of requests, Pattern 2 keeps workers warm.

## Why not several keys in one process

The runtime is a process-wide singleton. A second `init()` call shuts
the first runtime down, so one process cannot hold two keys at once.

The failure mode of forcing it is interleaved events: calls land on the
workflow of whichever key the runtime happens to hold, and the control center
shows a spend that belongs to no single workflow.

## One workflow across many processes

Every process that holds the same key reports to the same workflow.
Several workers with the same key produce one workflow record with the
combined spend.

## See also

- [Multi-agent orchestration](multi-agent-orchestration.md) — sub-agents
  inside one process
- [Concepts → API keys](../concepts/api-keys.md) — how a key binds to a
  workflow
- [Configuration → env vars](../getting-started/configuration.md)
