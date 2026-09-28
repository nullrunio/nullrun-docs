"""Screenshot the three `.nr-section` headings on the homepage.

Each section title is captured in the same viewport so the stray
attr_list paragraph and the h2 treatment are visible side by side.

Usage:  python scripts/shot_index.py [--base http://127.0.0.1:8811] [--out shots]
"""

from __future__ import annotations

import argparse
import pathlib
import sys

from playwright.sync_api import sync_playwright

SECTIONS = [
    "how-it-fits-together",
    "what-you-get-out-of-the-box",
    "what-one-protected-call-looks-like",
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
        ctx = browser.new_context(viewport={"width": 1440, "height": 1000})
        ctx.add_init_script(
            f"try {{ localStorage.setItem('nullrun-docs-theme', {args.theme!r}); }} catch (e) {{}}"
        )
        page = ctx.new_page()
        page.goto(f"{args.base}/index.html", wait_until="load")
        page.wait_for_timeout(1500)

        for anchor in SECTIONS:
            el = page.locator(f"#{anchor}")
            if not el.count():
                print(f"  MISSING #{anchor}")
                continue
            el.scroll_into_view_if_needed()
            page.wait_for_timeout(250)
            path = out / f"{args.theme}-{anchor}.png"
            page.screenshot(path=str(path))
            print(f"  {path}")

        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
