"""Render the Copernicus building-height raster into a small PNG that exactly
matches the map template's own projection, so the backdrop lines up
pixel-for-pixel with the plotted stops.

Why a rendered image instead of a live basemap: no tile server is reachable
from a published Claude artifact (or from this sandbox) -- see
docs/MILAN_DATA_DECISIONS.md, section 4. This uses the project's own
already-validated building-height data instead of leaving the map blank.

The projection replicated here has to match map/template.html's `project()`
function exactly: an equirectangular plot with a cos(latitude) correction on
longitude (so it reads as roughly true-shaped at Milan's latitude), plus a
fixed padding margin. It's re-derived here in Python rather than imported,
since the template's version runs in the browser -- if the map's PAD or
projection logic changes, this needs updating to match.
"""

import json
from pathlib import Path

import numpy as np
import rasterio
from PIL import Image
from rasterio.warp import Resampling, reproject

PROJECT_ROOT = Path(__file__).resolve().parents[3]
HEIGHT_RASTER = PROJECT_ROOT / "data_milan/seeds/building_height/IT002_MILANO_UA2012_DHM_V010.tif"
EXPOSURE_JSON = Path(__file__).resolve().parent / "data" / "exposure.json"
OUTPUT_DIR = Path(__file__).resolve().parent / "data"

PAD = 0.05
OUT_W = 760
MAX_HEIGHT_M = 60  # shading cap; a few very tall towers just top out the ramp
PLAIN_GRID_W = 1400

BUILDING_COLORS = ("#EDE2C8", "#AB9166")


def stop_bounds() -> tuple[float, float, float, float]:
    """Same bbox the map template derives from the exposure stops -- the
    backdrop has to be generated over the same extent the JS projection
    uses, not the raster's own extent.
    """
    with open(EXPOSURE_JSON) as f:
        stops = json.load(f)
    lons = [s["lo"] for s in stops]
    lats = [s["la"] for s in stops]
    return min(lons), max(lons), min(lats), max(lats)


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


def build_backdrop(height_grid, nodata, vb_w, vb_h, color_lo, color_hi, out_w) -> Image.Image:
    valid = height_grid != nodata
    t = np.clip(height_grid.astype(np.float32), 0, MAX_HEIGHT_M) / MAX_HEIGHT_M

    lo = np.array(hex_to_rgb(color_lo), dtype=np.float32)
    hi = np.array(hex_to_rgb(color_hi), dtype=np.float32)
    rgb = lo[None, None, :] + (hi - lo)[None, None, :] * t[:, :, None]

    h, w = height_grid.shape
    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    rgba[:, :, :3] = rgb.astype(np.uint8)
    rgba[:, :, 3] = np.where(valid, 235, 0).astype(np.uint8)
    img = Image.fromarray(rgba, "RGBA")

    out_h = round(out_w * vb_h / vb_w)
    inner_w, inner_h = round(out_w * (1 - 2 * PAD)), round(out_h * (1 - 2 * PAD))
    resized = img.resize((inner_w, inner_h), Image.LANCZOS)

    canvas = Image.new("RGBA", (out_w, out_h), (0, 0, 0, 0))
    canvas.paste(resized, (round(out_w * PAD), round(out_h * PAD)), resized)

    # Quantize RGB only, then reattach the untouched (smoothly antialiased at
    # the LANCZOS resize above) alpha mask -- quantizing all 4 channels
    # together dithers the alpha too and speckles the transparency.
    alpha = canvas.getchannel("A")
    rgb_quantized = canvas.convert("RGB").quantize(colors=40, method=Image.FASTOCTREE).convert("RGBA")
    rgb_quantized.putalpha(alpha)
    return rgb_quantized


def main() -> None:
    lon_min, lon_max, lat_min, lat_max = stop_bounds()
    lat_mid = (lat_min + lat_max) / 2
    cos_lat = np.cos(np.radians(lat_mid))
    w_deg = (lon_max - lon_min) * cos_lat
    h_deg = lat_max - lat_min
    vb_w, vb_h = 1000, round(1000 * h_deg / w_deg)

    height_grid, nodata = reproject_to_plain_grid(lon_min, lon_max, lat_min, lat_max)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    img = build_backdrop(height_grid, nodata, vb_w, vb_h, BUILDING_COLORS[0], BUILDING_COLORS[1], OUT_W)
    path = OUTPUT_DIR / "buildings.png"
    img.save(path, optimize=True)
    print(f"{path}: {path.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
