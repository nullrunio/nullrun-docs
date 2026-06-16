# HTTP API

> Placeholder — the canonical spec is in
> [`nullrunio/nullrun/contracts/openapi.yaml`](https://github.com/nullrunio/nullrun/blob/master/contracts/openapi.yaml).
> This page summarises the endpoints a typical SDK user cares about.

## Auth

All requests use `Authorization: Bearer $NULLRUN_API_KEY`. The
gateway validates the key, looks up the workspace, and applies the
workspace's policy to the request.

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/v1/check` | Pre-flight check (used by `@protect`) |
| `POST` | `/api/v1/track` | Report a call (cost, tokens, latency) |
| `POST` | `/api/v1/execute` | Synchronous policy decision for sensitive tools |
| `GET` | `/api/v1/policy` | Fetch the workspace policy |
| `PUT` | `/api/v1/workflows/{id}` | Update a workflow (budget, etc.) |
| `POST` | `/api/v1/workflows/{id}/kill` | Kill a running workflow |
| `POST` | `/api/v1/workflows/{id}/pause` | Pause a running workflow |

## See also

- [OpenAPI spec](https://github.com/nullrunio/nullrun/blob/master/contracts/openapi.yaml)
