"""Assemble the final, self-contained map HTML from template.html plus the
generated data files. Run the three prepare/render scripts first (or `make`
-- see README.md in this folder).

Output is a single HTML file with everything inlined (data, both backdrop
images as base64) -- no build step or server needed to view it, and nothing
it depends on lives outside this one file.
"""

from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE / "template.html"
DATA_DIR = HERE / "data"
OUTPUT = HERE / "dist" / "milan_heat_map.html"

PLACEHOLDERS = {
    "__DATA_JSON__": DATA_DIR / "exposure.json",
    "__WAIT_JSON__": DATA_DIR / "wait_time.json",
    "__ROADS_JSON__": None,  # no street-vector data yet -- see docs/MILAN_DATA_DECISIONS.md
}

IMAGE_PLACEHOLDERS = {
    "__BUILDINGS_LIGHT_B64__": DATA_DIR / "buildings_light.png",
    "__BUILDINGS_DARK_B64__": DATA_DIR / "buildings_dark.png",
}


def main() -> None:
    html = TEMPLATE.read_text(encoding="utf-8")

    for placeholder, path in PLACEHOLDERS.items():
        value = path.read_text(encoding="utf-8") if path else "[]"
        html = html.replace(placeholder, value)

    import base64

    for placeholder, path in IMAGE_PLACEHOLDERS.items():
        b64 = base64.b64encode(path.read_bytes()).decode("ascii")
        html = html.replace(placeholder, b64)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(html, encoding="utf-8")
    print(f"Wrote {OUTPUT} ({OUTPUT.stat().st_size / 1024 / 1024:.2f} MB)")


if __name__ == "__main__":
    main()
