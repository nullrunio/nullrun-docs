"""Screenshot each `.nr-mermaid` diagram in isolation.

Crops to the diagram element so node text wrapping and edge labels are
inspectable without the surrounding page.

Usage:  python scripts/shot_diagrams.py [--base http://127.0.0.1:8811]
"""

from __future__ import annotations

import argparse
import pathlib
import sys

from playwright.sync_api import sync_playwright

PAGES = [
    ("index", "/index.html"),
    ("ci-cd", "/how-to/ci-cd/index.html"),
    ("positioning", "/operations/framework-positioning/index.html"),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8811")
    ap.add_argument("--out", default="shots")
    ap.add_argument("--theme", default="light", choices=["light", "dark"])
    args = ap.parse_args()

    out = pathlib.Path(args.out)
    out.mkdir(exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1440, "height": 1200})
        ctx.add_init_script(
            f"try {{ localStorage.setItem('nullrun-docs-theme', {args.theme!r}); }} catch (e) {{}}"
        )
        page = ctx.new_page()

        for slug, path in PAGES:
            page.goto(f"{args.base}{path}", wait_until="load")
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
            n = page.locator(".nr-mermaid").count()
            for i in range(n):
                dest = out / f"{args.theme}-diagram-{slug}-{i}.png"
                page.locator(".nr-mermaid").nth(i).screenshot(path=str(dest))
                print(f"  {dest}")

        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
