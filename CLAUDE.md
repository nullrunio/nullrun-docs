# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

The source for **https://docs.nullrun.io** — a MkDocs Material site documenting NullRun, a runtime decision layer for tool-using AI agents. This repo contains **only documentation and the site build**; the SDK, gateway, and dashboard live in other repositories (`nullrun-sdk-python`, private `nullrun`).

## Commands

```bash
# Serve locally with live reload on http://127.0.0.1:8000
mkdocs serve

# Production build — the exact command CI runs. --strict turns
# warnings (broken nav entries, missing links) into failures, so always
# run it before declaring a change done.
mkdocs build --strict
```

No `requirements.txt` exists. CI (`.github/workflows/docs.yml`) installs `mkdocs`, `mkdocs-material`, `pymdown-extensions` directly. `infra/scripts/docsnav.py` also imports `mkdocs.config`, so the generator scripts need mkdocs present.

### Link verification

Two-step, and the order matters — the second script reads the first one's output at `/tmp/links.json`:

```bash
mkdocs build                                   # site/ must exist
python scripts/extract_links.py                # -> /tmp/links.json
python scripts/verify_internal_links.py         # -> /tmp/broken_links.json
```

`verify_internal_links.py` resolves relative Markdown links by walking the filesystem and validates `#anchor` fragments against the slugified heading ids in the built HTML. Run both after moving or renaming a page.

**Reading its output:** it reports **root-absolute** hrefs (`/assets/…`, `/stylesheets/extra.css`) as broken. They are not — the script joins them onto `SITE` as if relative, and on Windows a leading `/` makes the joined path absolute, so the existence check always misses. Expect ~55 such entries on a clean tree; ignore them and look at the relative-href entries instead.

It also currently reports `print/` as broken on all 48 nested pages. That one is **real**: `overrides/partials/header.html:96` hardcodes `href="print/"` as a relative URL, so the menu-bar print button only resolves from the site root and 404s on every page below it (the inline comment there claiming the relative form "works regardless of `use_directory_urls`" is wrong — relative links resolve against the *current page's* directory). Fixing it means emitting an absolute `/print/` from the site root.

### Screenshots

`python scripts/screenshot.py` captures light/dark pairs of the dashboard into `docs/assets/images/screenshots/`, outlined with a brand-yellow box marking the control being discussed. It needs the dashboard running and logged in; `--only <scenario>` limits the run. `scripts/add_descriptions.py` is a **one-shot** migration that back-filled `description:` front matter — it is a no-op on files that already have the key and is not part of any routine workflow.

## Architecture

### Navigation is the source of truth

`mkdocs.yml`'s `nav:` tree is not just a sidebar. It is the input to three separate things:

1. The rendered sidebar.
2. `docs/llms-full.txt` — the single-fetch corpus for agents, built by `infra/scripts/build-llms-full.py`.
3. `docs/print.md` — the printable single-page edition, built by `infra/scripts/build-print.py`.

**Adding or moving a page means editing `nav:` *and* regenerating both artifacts**, in nav order:

```bash
python infra/scripts/build-llms-full.py    # -> docs/llms-full.txt
python infra/scripts/build-print.py        # -> docs/print.md
python infra/scripts/build-print.py --check # CI staleness check
```

`infra/scripts/docsnav.py` holds the shared nav-reading and heading-slug logic so neither generator re-derives it. Its `slugify` deliberately mirrors Python-Markdown's `toc` slugify — diverging from it would point every anchor in the generated TOC at an id the renderer never emits.

`docs/llms.txt` (the structured index) is hand-maintained, unlike the two generated files.

**Never hand-edit `docs/llms-full.txt` or `docs/print.md`** — the next generator run overwrites them. Both are byte-identical after a regeneration on a clean tree, so `git status` staying clean is the check that they're in sync.

Note that `.gitignore` excludes `infra/`, so these three generator scripts are **untracked** — they exist only in this working copy and won't survive a fresh clone. Their *outputs* are tracked. If a task needs them and they're missing, that's why.

### The no-internals rule

`build-llms-full.py` enforces that internal implementation details never reach reader-facing docs, by **failing and naming the offending page** — not by substituting tokens away. Rewriting them would let the corpus silently drift from the Markdown it claims to mirror. `FORBIDDEN_WORDS` covers internal storage tables (`audit_events`, `overdraft_used`, `organization_api_keys`), internal service names (`breaker-core`, `gate-core`, `prod-guard`), and internal class names (`ApproximateBudget`, `AlertListMeta`).

The list holds only unambiguous names. `approval_rules` and `secret_key` are deliberately **absent** — both are documented public API fields, so flagging them would fail on correct prose. The check is whole-word, so `approved` or a Redis URL in a user config doesn't trip it. `compliance/data-handling.md` is waived for the storage-table half, since that page names the fields it stores on purpose.

If the build fails on a token that is genuinely reader-facing, add it to `FORBIDDEN_WORDS`' neighbours in the comments — don't delete the page's prose.

### Theming: three layers over Material

The site is a heavily re-skinned Material theme. Changes usually land in one of three places, and the choice matters:

- **`overrides/`** — Jinja template overrides via `theme.custom_dir`. `main.html` extends the upstream template and only overrides the `extrahead` block (brand `@font-face`, OG/Twitter meta, CSP/Referrer-Policy `<meta http-equiv>`). `partials/header.html` replaces Material's full-height branded header with a slim ~50px Helix-style menu-bar. `partials/footer.html` is intentionally **empty** — there is no footer and no prev/next pager, so `navigation.footer` is off in `mkdocs.yml` and navigation happens through the left sidebar only.
- **`docs/stylesheets/extra.css`** — the neo-brutalist re-skin. Mirrors the product's `frontend/app/globals.css` tokens 1:1 (cream paper `#F1EDDA` / machined ink `#1A1A1A`, FLAG `#E6AF1E`, BLOCK `#D1372B`, Allow `#1E8A59`). Its header comment carries the layout diagram and the sidebar (fixed 340px) + menu-bar + content column geometry.
- **`docs/javascripts/extra.js`** — six numbered hooks, each documented in the file header: theme picker, sidebar hide toggle, search-dialog dismissal, print-page body class, mobile drawer, and the Mermaid loader. State persists in `localStorage` under both our keys and Material's own (`__palette`).

Layout is 2-column, not Material's default 3-column: the sidebar is the primary navigation and the right-hand TOC appears only on long pages. The sidebar sections are numbered (`1.`, `2.`, `2.1.` …) and those numbers are load-bearing — `print.md` renumbers its headings to match them.

### Mermaid diagrams are self-hosted, deliberately

`mkdocs.yml` registers a `pymdownx.superfences` custom fence that emits `class="nr-mermaid"`, **not** Material's stock `mermaid`. Material's bundle watches for `.mermaid`, claims those nodes, and lazily fetches the runtime from unpkg.com — which the site CSP (`script-src 'self'`) blocks, leaving every diagram as a raw code block. The runtime is vendored at `docs/javascripts/mermaid.min.js` and loaded lazily, only on pages that contain a diagram, re-running on Material's SPA navigation and re-rendering on theme switch.

Don't "fix" the fence class to plain `mermaid`.

### Deploy: two origins, one active

`docs.nullrun.io` currently resolves to GitHub Pages via the `CNAME` file at the repo root. The workflow copies `CNAME` into `site/` explicitly because mkdocs only copies the `docs/` tree, and without it the custom domain 404s on every request. A Cloudflare Pages migration is staged but not merged (`docs/_headers` carries the six headers GitHub Pages can't serve; `overrides/main.html` covers CSP and Referrer-Policy via the `<meta http-equiv>` fallback that works on any host).

The README's deployment section is the canonical record of this — read it before touching either.

## Conventions

- **Front matter on every page**: `title:`, `description:`, and `maturity:` (`stable` or `beta`) where applicable. `description` is load-bearing — Material otherwise falls back to the first paragraph (usually just the section title), and the JSON-LD injector in `main.html` needs an explicit one to emit a TechArticle node. Per-page `image:` overrides the OG card.
- **No temporal framing** — see the rule below.
- `validation.nav.omitted_files: ignore` in `mkdocs.yml` exists so `llms.txt` / `llms-full.txt` can live in `docs/` without tripping `--strict`. Leave it.
- `mkdocs.yml` carries dense explanatory comments about *why* each theme feature and Markdown extension is enabled ("every one of these is load-bearing"). Read them before changing anything there — several features look like no-ops but are load-bearing for specific pages.

## Hard rules

**Documentation describes the current state only.** Never write "X was renamed to Y", "X is deprecated", "previously / before / in older versions", or any other temporal framing of a change. Rewrite the affected section to describe what the API *is*; don't preserve an old name as an alias, don't add a "breaking change" callout, and don't add migration notes to the body of a reference page. NullRun has no users yet, so there is no legacy audience to address and temporal framing is pure noise. The changelog is the only place it belongs.

**Verify the SDK surface before documenting it.** Symbol names, error codes, and decorator signatures change between releases, and documented surface has drifted from reality before. Before editing `docs/reference/sdk-api.md`, `docs/reference/errors.md`, or any how-to, confirm against the SDK checkout rather than against the docs themselves:

```bash
python -c "import nullrun; print(sorted(nullrun.__all__))"
```

Some symbols are lazy-loaded via PEP 562 `__getattr__` and so do **not** appear in `__all__` — check `_LAZY_EXPORTS` for context managers (`workflow`, `span`, `agent`, `chain`) and the extra exceptions. Do not document code that is defined but never raised, or states that are declared but unreachable.
