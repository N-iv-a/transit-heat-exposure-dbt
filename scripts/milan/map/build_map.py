"""Assemble the final, self-contained map HTML from template.html plus the
generated data files. Run the three prepare/render scripts first (or `make`
-- see README.md in this folder).

Output is a single HTML file with everything inlined (data, the backdrop
image as base64) -- no build step or server needed to view it, and nothing
it depends on lives outside this one file.
"""

import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE / "template.html"
DATA_DIR = HERE / "data"
VENDOR_DIR = HERE / "vendor"
OUTPUT = HERE / "dist" / "milan_heat_map.html"

PLACEHOLDERS = {
    "__DATA_JSON__": DATA_DIR / "exposure.json",
    "__WAIT_JSON__": DATA_DIR / "wait_time.json",
    "__MAIN_DATA_JSON__": DATA_DIR / "main.json",
    "__ROADS_JSON__": None,  # no street-vector data yet -- see docs/MILAN_DATA_DECISIONS.md
}

IMAGE_PLACEHOLDERS = {
    "__BUILDINGS_B64__": DATA_DIR / "buildings.png",
    "__BUILDINGS_DECK_B64__": DATA_DIR / "buildings_deck.png",
}

# deck.gl UMD bundle inlined as a <script> body, not fetched -- this is what
# keeps the main view working with no network request. `</script` (any case)
# has to be escaped or it would prematurely close the wrapping <script> tag
# once this text lands inside template.html.
SCRIPT_CLOSE_RE = re.compile(r"</script", re.IGNORECASE)


def main() -> None:
    html = TEMPLATE.read_text(encoding="utf-8")

    for placeholder, path in PLACEHOLDERS.items():
        value = path.read_text(encoding="utf-8") if path else "[]"
        html = html.replace(placeholder, value)

    deckgl_js = (VENDOR_DIR / "deck.gl-9.4.0.min.js").read_text(encoding="utf-8")
    deckgl_js = SCRIPT_CLOSE_RE.sub("<\\/script", deckgl_js)
    html = html.replace("__DECKGL_JS__", deckgl_js)

    import base64

    for placeholder, path in IMAGE_PLACEHOLDERS.items():
        b64 = base64.b64encode(path.read_bytes()).decode("ascii")
        html = html.replace(placeholder, b64)

    known = set(PLACEHOLDERS) | set(IMAGE_PLACEHOLDERS) | {"__DECKGL_JS__"}
    leftover = sorted(p for p in known if p in html)
    assert not leftover, f"Unfilled placeholders remain: {leftover}"

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(html, encoding="utf-8")
    print(f"Wrote {OUTPUT} ({OUTPUT.stat().st_size / 1024 / 1024:.2f} MB)")


if __name__ == "__main__":
    main()
