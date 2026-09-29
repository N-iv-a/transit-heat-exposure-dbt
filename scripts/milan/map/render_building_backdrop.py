"""Render the Copernicus building-height raster into `data/buildings_deck.png`,
the map's backdrop: a plain lon/lat grid (WGS84, no padding margin) over the
exact bounds in `data/main.json`, dropped straight into a deck.gl
`BitmapLayer` with those bounds. `render_shadow_layers.py` renders the hourly
shadow overlays over the same bounds, so both line up pixel for pixel.

Why a rendered image instead of a live basemap: no tile server is reachable
from a published Claude artifact (or from this sandbox) -- see
docs/MILAN_DATA_DECISIONS.md, section 4. This uses the project's own
already-validated building-height data instead of leaving the map blank.
"""

import json
from pathlib import Path

import numpy as np
import rasterio
from PIL import Image
from rasterio.warp import Resampling, reproject

PROJECT_ROOT = Path(__file__).resolve().parents[3]
HEIGHT_RASTER = PROJECT_ROOT / "data_milan/seeds/building_height/IT002_MILANO_UA2012_DHM_V010.tif"
MAIN_JSON = Path(__file__).resolve().parent / "data" / "main.json"
OUTPUT_DIR = Path(__file__).resolve().parent / "data"
DECK_GRID_W = 900

MAX_HEIGHT_M = 60  # shading cap; a few very tall towers just top out the ramp
PLAIN_GRID_W = 1400

BUILDING_COLORS = ("#EDE2C8", "#AB9166")


def hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def reproject_to_plain_grid(lon_min, lon_max, lat_min, lat_max):
    plain_h = round(PLAIN_GRID_W * (lat_max - lat_min) / (lon_max - lon_min))
    dst_transform = rasterio.transform.from_bounds(lon_min, lat_min, lon_max, lat_max, PLAIN_GRID_W, plain_h)

    with rasterio.open(HEIGHT_RASTER) as src:
        dst = np.full((plain_h, PLAIN_GRID_W), src.nodata, dtype=src.dtypes[0])
        reproject(
            source=rasterio.band(src, 1),
            destination=dst,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=dst_transform,
            dst_crs="EPSG:4326",
            resampling=Resampling.average,
            dst_nodata=src.nodata,
        )
        nodata = src.nodata
    return dst, nodata


def build_plain_backdrop(height_grid, nodata, color_lo, color_hi) -> Image.Image:
    """RGBA image of the height grid, light to dark with height. deck.gl's
    BitmapLayer maps the pixel grid straight onto the lon/lat bounds, so the
    image aspect ratio is the bounds' aspect ratio already.
    """
    valid = height_grid != nodata
    t = np.clip(height_grid.astype(np.float32), 0, MAX_HEIGHT_M) / MAX_HEIGHT_M

    lo = np.array(hex_to_rgb(color_lo), dtype=np.float32)
    hi = np.array(hex_to_rgb(color_hi), dtype=np.float32)
    rgb = lo[None, None, :] + (hi - lo)[None, None, :] * t[:, :, None]

    h, w = height_grid.shape
    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    rgba[:, :, :3] = rgb.astype(np.uint8)
    rgba[:, :, 3] = np.where(valid, 235, 0).astype(np.uint8)
    return Image.fromarray(rgba, "RGBA")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(MAIN_JSON) as f:
        lon_min, lat_min, lon_max, lat_max = json.load(f)["bounds"]
    height_grid, nodata = reproject_to_plain_grid(lon_min, lon_max, lat_min, lat_max)
    img = build_plain_backdrop(height_grid, nodata, BUILDING_COLORS[0], BUILDING_COLORS[1])
    grid_h, grid_w = height_grid.shape
    img = img.resize((DECK_GRID_W, round(DECK_GRID_W * grid_h / grid_w)), Image.LANCZOS)
    path = OUTPUT_DIR / "buildings_deck.png"
    img.save(path, optimize=True)
    print(f"{path}: {path.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
