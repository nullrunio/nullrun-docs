"""Audit every `.nr-mermaid` diagram in the built site.

Loads each page that contains a diagram in both colour schemes and
reports, per node: whether an SVG landed inside it, whether the node
is actually visible (`data-nr-mermaid-rendered` set), and any console
error the Mermaid runtime emitted. Also sweeps *all* pages for
console errors and for diagram nodes that never render, so a
regression on a page we did not think to check still shows up.

Usage:  python scripts/check_mermaid.py [--base http://127.0.0.1:8811]
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

from playwright.sync_api import sync_playwright

# Any page that ships a ```mermaid fence. Kept explicit so the deep
# check stays fast; the sweep below covers the rest of the site.
DIAGRAM_PAGES = [
    "/index.html",
    "/how-to/ci-cd/index.html",
    "/operations/framework-positioning/index.html",
]

# Console noise that is not ours and not actionable here.
IGNORE_CONSOLE = re.compile(
    r"favicon|Download the React DevTools|source-?map|Failed to load resource.*404"
)

# The site has its own theme picker (extra.js §1): it reads
# `nullrun-docs-theme` from localStorage and maps it onto Material's
# `data-md-color-scheme`. Seeding that key before the first paint is
# the only way to get a real dark-mode render — `color_scheme` on the
# browser context is ignored because the attribute always wins.
THEMES = {"light": "default", "dark": "slate"}


def audit_page(page, url: str) -> tuple[list[dict], list[str]]:
    errors: list[str] = []
    page.on(
        "console",
        lambda m: errors.append(f"{m.type}: {m.text}")
        if m.type in ("error", "warning") and not IGNORE_CONSOLE.search(m.text)
        else None,
    )
    page.goto(url, wait_until="load")
    # The runtime is injected lazily and only resolves once the 2.5 MB
    # bundle has executed, so wait on the reveal attribute rather than a
    # fixed delay.
    try:
        page.wait_for_function(
            "() => { const n = document.querySelectorAll('.nr-mermaid');"
            " return n.length === 0 ||"
            " [...n].every(x => x.hasAttribute('data-nr-mermaid-rendered')); }",
            timeout=20_000,
        )
    except Exception:
        pass
    page.wait_for_timeout(300)

    nodes = page.eval_on_selector_all(
        ".nr-mermaid",
        """els => els.map((el, i) => {
            const svg = el.querySelector('svg');
            const r = el.getBoundingClientRect();
            return {
                i,
                hasSvg: !!svg,
                svgW: svg ? Math.round(svg.getBoundingClientRect().width) : 0,
                svgH: svg ? Math.round(svg.getBoundingClientRect().height) : 0,
                revealed: el.hasAttribute('data-nr-mermaid-rendered'),
                visible: getComputedStyle(el).visibility === 'visible',
                boxW: Math.round(r.width),
                boxH: Math.round(r.height),
                scheme: document.body.getAttribute('data-md-color-scheme'),
                text: el.textContent.trim().slice(0, 60),
            };
        })""",
    )
    return nodes, errors


def open_ctx(browser, theme: str):
    ctx = browser.new_context()
    ctx.add_init_script(
        f"try {{ localStorage.setItem('nullrun-docs-theme', {theme!r}); }} catch (e) {{}}"
    )
    return ctx


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8811")
    ap.add_argument("--sweep", action="store_true",
                    help="also load every page in the site and report console errors")
    args = ap.parse_args()

    failures: list[str] = []
    checked = 0

    with sync_playwright() as p:
        browser = p.chromium.launch()
        for theme in THEMES:
            ctx = open_ctx(browser, theme)
            page = ctx.new_page()
            for path in DIAGRAM_PAGES:
                url = args.base + path
                nodes, errors = audit_page(page, url)
                checked += len(nodes)
                print(f"\n[{theme}] {path}  ({len(nodes)} diagram(s))")
                for n in nodes:
                    ok = n["hasSvg"] and n["revealed"] and n["visible"] and n["svgW"] > 0
                    print(
                        f"   {'OK  ' if ok else 'FAIL'} #{n['i']} "
                        f"scheme={n['scheme']} svg={n['svgW']}x{n['svgH']} "
                        f"box={n['boxW']}x{n['boxH']} "
                        f"revealed={n['revealed']} visible={n['visible']}"
                    )
                    if not ok:
                        failures.append(f"[{theme}] {path} #{n['i']} :: {n['text']!r}")
                for e in errors:
                    print(f"   console {e}")
                    failures.append(f"[{theme}] {path} console: {e}")
            ctx.close()

        if args.sweep:
            root = pathlib.Path("site")
            total = 0
            for html in sorted(root.rglob("*.html")):
                rel = html.relative_to(root).as_posix()
                total += 1
                ctx = open_ctx(browser, "light")
                page = ctx.new_page()
                nodes, errors = audit_page(page, f"{args.base}/{rel}")
                bad = [n for n in nodes if not (n["hasSvg"] and n["revealed"])]
                if errors or bad:
                    print(f"\n[sweep] /{rel}")
                    for n in bad:
                        print(f"   FAIL #{n['i']} hasSvg={n['hasSvg']} revealed={n['revealed']}")
                        failures.append(f"[sweep] /{rel} #{n['i']} did not render")
                    for e in errors:
                        print(f"   console {e}")
                        failures.append(f"[sweep] /{rel} console: {e}")
                ctx.close()
            print(f"\n[sweep] loaded {total} pages")

        browser.close()

    print(f"\n{'=' * 60}")
    print(f"checked {checked} diagram render(s)")
    if failures:
        print(f"{len(failures)} FAILURE(S):")
        for f in failures:
            print("  -", f)
        return 1
    print("all diagrams render in both schemes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
