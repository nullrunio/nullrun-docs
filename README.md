# NullRun Docs

Исходники сайта **[docs.nullrun.io](https://docs.nullrun.io)**.

## Что внутри

- **[Getting started](docs/getting-started/install.md)** — установка,
  квикстарт, конфигурация SDK.
- **[Concepts](docs/concepts/circuit-breaker.md)** — как устроены
  бюджеты, circuit breaker, control plane, sensitive tools,
  workflow context.
- **[How-to](docs/how-to/langgraph.md)** — рецепты для конкретных
  фреймворков и сценариев (LangGraph, OpenAI Agents, cost cap).
- **[Reference](docs/reference/sdk-api.md)** — полный SDK / HTTP API
  / справочник кодов ошибок.

## С чего начать

| Если вы... | Откройте |
| --- | --- |
| Хотите попробовать за 5 минут | [Quickstart](https://docs.nullrun.io/getting-started/quickstart/) |
| Подключаете SDK в проде | [Configuration](https://docs.nullrun.io/getting-started/configuration/) |
| Считаете бюджет | [Budgets](https://docs.nullrun.io/concepts/budgets/) + [Cost cap how-to](https://docs.nullrun.io/how-to/cost-cap/) |
| Используете LangGraph | [How-to → LangGraph](https://docs.nullrun.io/how-to/langgraph/) |
| Используете OpenAI Agents | [How-to → OpenAI Agents](https://docs.nullrun.io/how-to/openai-agents/) |
| Ловите 4xx / 5xx | [Error codes](https://docs.nullrun.io/reference/errors/) |
| Хотите увидеть SDK API целиком | [SDK API reference](https://docs.nullrun.io/reference/sdk-api/) |

## Полный список страниц

**Getting started**
- [Install](docs/getting-started/install.md) · `pip install nullrun`, API-ключ, auto-instrumentation
- [Quickstart](docs/getting-started/quickstart.md) · `@protect` за 30 строк
- [Configuration](docs/getting-started/configuration.md) · env vars, fallback modes, gRPC status

**Concepts**
- [Circuit breaker](docs/concepts/circuit-breaker.md) · CLOSED / OPEN / HALF_OPEN
- [Budgets](docs/concepts/budgets.md) · pre-flight `/check` + reservation `/execute`
- [Sensitive tools](docs/concepts/sensitive-tools.md) · fail-CLOSED навсегда
- [Workflow context](docs/concepts/workflow.md) · `nullrun.workflow(...)` и его роль
- [Control plane (WebSocket)](docs/concepts/control-plane.md) · kill / pause в реальном времени

**How-to**
- [Protect a LangGraph agent](docs/how-to/langgraph.md)
- [Use with OpenAI Agents](docs/how-to/openai-agents.md)
- [Set a hard cost cap](docs/how-to/cost-cap.md)

**Reference**
- [SDK API](docs/reference/sdk-api.md) · `init`, `@protect`, `@sensitive`, `workflow`, exceptions
- [HTTP API](docs/reference/http-api.md) · `/track`, `/gate`, `/check`, `/execute`, WebSocket
- [Error codes](docs/reference/errors.md) · `validation_error`, `RateLimitError`, kill contract

## Что вам понадобится с нашей стороны

- **API key** — создаётся в [nullrun.io](https://nullrun.io) → Settings → API keys.
  Даётся пара `nr_live_…` + HMAC-секрет.
- **Python ≥ 3.10** для SDK.
- **Никакого self-host для чтения документации** — сайт публичный.

## Другие репозитории NullRun

- [nullrun-sdk-python](https://github.com/nullrunio/nullrun-sdk-python) — Python SDK (`pip install nullrun`)
- [nullrun-examples](https://github.com/nullrunio/nullrun-examples) — рабочие примеры
- [.github](https://github.com/nullrunio/.github) — профиль организации, SECURITY / SUPPORT
- `nullrun` — gateway + dashboard (приватный репозиторий, доступ по запросу)
