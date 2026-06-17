# nullrun-docs

User-facing documentation for NullRun, built with
[MkDocs Material](https://squidfunk.github.io/mkdocs-material/) and
deployed to <https://docs.nullrun.io>.

## Build locally

```bash
pip install mkdocs mkdocs-material pymdown-extensions
mkdocs serve
```

## Deploy

Pushing to `master` triggers `.github/workflows/docs.yml`, which builds
the site and publishes it via GitHub Pages. The custom domain
(`docs.nullrun.io`) is wired up through the `CNAME` file at the repo
root.

For a one-off local deploy without the workflow:

```bash
mkdocs gh-deploy
```

### First-time setup

If you forked the repo, the deploy won't start on its own. In the GitHub
UI:

1. **Settings → Pages → Source:** "GitHub Actions".
2. **DNS at the registrar** (netim.net) — point `docs.nullrun.io` at
   GitHub Pages. Either:
   - Four `A` records: `185.199.108.153`, `185.199.109.153`,
     `185.199.110.153`, `185.199.111.153`, **or**
   - One `CNAME` record: `docs` → `nullrunio.github.io`.
3. The first workflow run after Pages is enabled publishes the site at
   <https://docs.nullrun.io>. Subsequent pushes to `master` redeploy
   automatically.

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
