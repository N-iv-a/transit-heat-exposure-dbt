"""Render og.png (1200x627, Open Graph / Twitter card image) from the site.

Serves dist/site over a local http.server, opens it in headless Chromium via
Playwright and screenshots the top of the page. The result is versioned in
this folder (og.png) so CI and build_map.py never need a browser: build_map.py
just copies it into dist/site/. Re-run this by hand when the page changes:

    python3 build_map.py && python3 render_og_image.py && python3 build_map.py

Needs the python `playwright` package and a Chromium (set
PLAYWRIGHT_BROWSERS_PATH if it is not in the default location).
"""

import functools
import http.server
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
SITE = HERE / "dist" / "site"
OUTPUT = HERE / "og.png"
WIDTH, HEIGHT = 1200, 627


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def main() -> None:
    handler = functools.partial(_Quiet, directory=str(SITE))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_address[1]}/index.html"
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={"width": WIDTH, "height": HEIGHT})
            page.goto(url)
            page.wait_for_selector(".stat .n", timeout=30000)
            page.wait_for_timeout(3000)  # let the deck.gl layers draw
            page.screenshot(path=str(OUTPUT))
            browser.close()
    finally:
        server.shutdown()
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
