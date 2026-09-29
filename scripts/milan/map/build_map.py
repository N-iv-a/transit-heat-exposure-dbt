"""Assemble the map from template.html plus the generated data files.
Run the prepare/render scripts first (see README.md in this folder).

One template, two outputs:
  * dist/site/            static site: index.html + data/*.json + data/*.png +
                          vendor/deck.gl-*.min.js (+ og.png if versioned here).
                          The page fetches its data with relative URLs, so it
                          needs HTTP (local server or GitHub Pages).
  * dist/milan_heat_map.html   single self-contained file (data, images and
                          deck.gl inlined) that works from file:// offline.

The tree data (data/trees.json, ~3 MB) is a separate file on the site, fetched
the first time the Trees view opens. In the single file it is inlined too,
unless the file would exceed SINGLE_MAX_MB: then only the trees that shade a
stop are inlined and the Trees view says the full map is on the site.

The 7 hourly shadow overlays (data/shadow_13.png .. shadow_19.png, made by
render_shadow_layers.py, ~0.5 MB together) go into both outputs. If the single
file would still exceed SINGLE_TOTAL_MB it ships without them (the page then
says the shadow overlay is on the site).
"""

import base64
import json
import re
import shutil
from pathlib import Path

import prepare_tree_data as trees_mod
import render_shadow_layers as shadow_mod

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE / "template.html"
DATA_DIR = HERE / "data"
VENDOR_DIR = HERE / "vendor"
DIST = HERE / "dist"
SITE = DIST / "site"
SINGLE = DIST / "milan_heat_map.html"
OG_IMAGE = HERE / "og.png"  # versioned, made by render_og_image.py

DECK_NAME = "deck.gl-9.4.0.min.js"
JSON_FILES = {"main": "main.json", "exposure": "exposure.json", "wait": "wait_time.json"}
TREES_FILE = "trees.json"
SINGLE_MAX_MB = 12
SINGLE_TOTAL_MB = 13
BACKDROP = "buildings_deck.png"
SHADOWS = {hour: shadow_mod.shadow_file(hour) for hour in shadow_mod.HOURS}
IMAGES = [BACKDROP, *SHADOWS.values()]

PLACEHOLDERS = [
    "__DECKGL_TAG__",
    "__INLINE_DATA__",
    "__BUILDINGS_DECK_URL__",
    "__SHADOW_URLS__",
]

# `</script` (any case) inside inlined text would close the wrapping <script>.
SCRIPT_CLOSE_RE = re.compile(r"</script", re.IGNORECASE)


def _escape_script(text: str) -> str:
    return SCRIPT_CLOSE_RE.sub("<\\/script", text)


def _fill(template: str, values: dict[str, str]) -> str:
    # str.replace with a callable-free approach: plain replace is fine, values
    # are never re-scanned for placeholders because each key is replaced once.
    for key, value in values.items():
        template = template.replace(key, value)
    leftover = [p for p in PLACEHOLDERS if p in template]
    assert not leftover, f"Unfilled placeholders remain: {leftover}"
    return template


def _data_uri(name: str) -> str:
    return "data:image/png;base64," + base64.b64encode((DATA_DIR / name).read_bytes()).decode("ascii")


def _shading_subset(trees: dict) -> dict:
    """Keep only the trees that shade a stop (re-encoding the delta columns)."""
    keep = trees["s"]
    x, y = trees_mod.undelta(trees["x"]), trees_mod.undelta(trees["y"])
    return {
        **{k: trees[k] for k in ("lon0", "lat0", "scale", "species", "genera")},
        "n": len(keep),
        "x": trees_mod.delta([x[i] for i in keep]),
        "y": trees_mod.delta([y[i] for i in keep]),
        "h": [trees["h"][i] for i in keep],
        "c": [trees["c"][i] for i in keep],
        "sp": [trees["sp"][i] for i in keep],
        "s": list(range(len(keep))),
        "partial": True,
        "total": trees["n"],
    }


def build_single(template: str) -> None:
    deck_js = _escape_script((VENDOR_DIR / DECK_NAME).read_text(encoding="utf-8"))
    inline = (
        "{"
        + ",".join(
            f'"{key}":{(DATA_DIR / fname).read_text(encoding="utf-8").strip()}'
            for key, fname in JSON_FILES.items()
        )
        + "}"
    )
    trees_text = (DATA_DIR / TREES_FILE).read_text(encoding="utf-8").strip()
    backdrop_bytes = (DATA_DIR / BACKDROP).stat().st_size * 4 // 3
    shadow_bytes = sum((DATA_DIR / n).stat().st_size for n in SHADOWS.values()) * 4 // 3
    base_mb = (len(deck_js) + len(inline) + len(template) + backdrop_bytes) / 1024 / 1024
    if base_mb + len(trees_text) / 1024 / 1024 > SINGLE_MAX_MB:
        trees_text = json.dumps(_shading_subset(json.loads(trees_text)), separators=(",", ":"), ensure_ascii=False)
        print(f"note: single file would exceed {SINGLE_MAX_MB} MB, inlining only the shading trees")
    inline = inline[:-1] + ',"trees":' + trees_text + "}"
    total_mb = base_mb + len(trees_text) / 1024 / 1024 + shadow_bytes / 1024 / 1024
    shadow_urls = {str(h): _data_uri(n) for h, n in SHADOWS.items()}
    if total_mb > SINGLE_TOTAL_MB:
        shadow_urls = {}
        print(f"note: single file would exceed {SINGLE_TOTAL_MB} MB, leaving out the shadow overlay")
    html = _fill(
        template,
        {
            # deck.gl goes last-ish: it is big, and must not be re-scanned
            "__BUILDINGS_DECK_URL__": _data_uri(BACKDROP),
            "__SHADOW_URLS__": json.dumps(shadow_urls),
            "__INLINE_DATA__": _escape_script(inline),
            "__DECKGL_TAG__": f"<script>{deck_js}</script>",
        },
    )
    SINGLE.parent.mkdir(parents=True, exist_ok=True)
    SINGLE.write_text(html, encoding="utf-8")
    print(f"Wrote {SINGLE} ({SINGLE.stat().st_size / 1024 / 1024:.2f} MB)")


def build_site(template: str) -> None:
    if SITE.exists():
        shutil.rmtree(SITE)
    (SITE / "data").mkdir(parents=True)
    (SITE / "vendor").mkdir()

    for fname in [*JSON_FILES.values(), TREES_FILE, *IMAGES]:
        shutil.copy2(DATA_DIR / fname, SITE / "data" / fname)
    shutil.copy2(VENDOR_DIR / DECK_NAME, SITE / "vendor" / DECK_NAME)
    if OG_IMAGE.exists():
        shutil.copy2(OG_IMAGE, SITE / "og.png")
    else:
        print("note: og.png not found -- run render_og_image.py to create it")

    html = _fill(
        template,
        {
            "__BUILDINGS_DECK_URL__": f"data/{BACKDROP}",
            "__SHADOW_URLS__": json.dumps({str(h): f"data/{n}" for h, n in SHADOWS.items()}),
            "__INLINE_DATA__": "null",
            "__DECKGL_TAG__": f'<script src="vendor/{DECK_NAME}"></script>',
        },
    )
    (SITE / "index.html").write_text(html, encoding="utf-8")

    total = 0
    for f in sorted(SITE.rglob("*")):
        if f.is_file():
            total += f.stat().st_size
            print(f"  {f.relative_to(SITE)}: {f.stat().st_size / 1024:.0f} KB")
    print(f"Wrote {SITE} ({total / 1024 / 1024:.2f} MB)")


def main() -> None:
    template = TEMPLATE.read_text(encoding="utf-8")
    # data/trees.json and the shadow PNGs are made here, so the build command in loop.json stays unchanged
    trees_mod.main()
    shadow_mod.main()
    for name in [*JSON_FILES.values(), TREES_FILE, *IMAGES]:
        path = DATA_DIR / name
        assert path.exists() and path.stat().st_size > 0, f"{path} missing or empty"
        if name.endswith(".json"):
            json.loads(path.read_text(encoding="utf-8"))  # must parse
    build_site(template)
    build_single(template)


if __name__ == "__main__":
    main()
