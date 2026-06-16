# nullrun-docs

User-facing documentation for NullRun, built with
[MkDocs Material](https://squidfunk.github.io/mkdocs-material/) and
deployed to <https://docs.nullrun.io>.

## Build locally

```bash
pip install mkdocs mkdocs-material
mkdocs serve
```

## Deploy

```bash
mkdocs gh-deploy
```

This builds the static site and pushes it to the `gh-pages` branch of
this repo. The custom domain (`docs.nullrun.io`) is configured via the
`CNAME` file at the repo root.

## Structure

```
docs/
  index.md                 # landing page
  getting-started/         # install, quickstart, configuration
  concepts/                # circuit breaker, budgets, sensitive tools, workflow
  how-to/                  # langgraph, openai-agents, cost cap
  reference/               # SDK API, HTTP API, error codes
```

## Contributing

PRs welcome. Each page should be readable in under 5 minutes. Use
admonitions (`!!! note`, `!!! warning`) sparingly. Code samples should
be runnable as-is, with imports at the top of the file.
