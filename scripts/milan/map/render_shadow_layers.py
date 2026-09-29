"""Render the building-shadow overlay, one transparent PNG per hour (13..19
CEST), aligned with the backdrop `data/buildings_deck.png`: same lon/lat
bounds (the ones in `data/main.json`), plain WGS84 grid, so the page drops
each PNG into a deck.gl `BitmapLayer` with the backdrop's bounds.

The shadow mask is the algorithm of scripts/milan/solar_exposure.py
(`is_in_building_shadow`), vectorized over every pixel: from the pixel centre,
march toward the sun's azimuth in STEP_M steps up to the hour's search radius
and flag the pixel if a building at distance d is at least
d * tan(elevation) tall. Sun position, search radius, step and the required
height are the functions/constants of solar_exposure.py, imported, not copied.
The shadow is the one cast on the ground at that hour (what a stop sees).

Run after prepare_main_data.py (bounds) -- see README.md.
"""

import json
import math
import sys
import datetime
from pathlib import Path

import numpy as np
import rasterio
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import solar_exposure as se  # noqa: E402

HERE = Path(__file__).resolve().parent
MAIN_JSON = HERE / "data" / "main.json"
OUTPUT_DIR = HERE / "data"
GRID_W = 1400  # same width as the backdrop's plain grid (~13 m per pixel)
SHADOW_RGBA = (24, 32, 72, 120)  # cool dark blue; alpha is the overlay's own, layer opacity multiplies it
HOURS = list(se.CRITICAL_HOURS)


def shadow_file(hour: int) -> str:
    return f"shadow_{hour}.png"


def shadow_mask(band, transform, nodata, xs, ys, azimuth_deg, elevation_deg, radius_m, step_m=se.STEP_M):
    """Boolean array, same shape as xs/ys (EPSG:3035 metres): True where a
    building shades the point. Vectorized twin of se.is_in_building_shadow."""
    az = math.radians(azimuth_deg)
    dx, dy = math.sin(az), math.cos(az)
    inv = ~transform
    n_rows, n_cols = band.shape
    shadow = np.zeros(xs.shape, dtype=bool)
    distance = step_m
    while distance <= radius_m:
        # same cell lookup as raster.index(): floor of the inverse affine
        col_f, row_f = inv @ (xs + distance * dx, ys + distance * dy)
        row, col = np.floor(row_f).astype(np.int64), np.floor(col_f).astype(np.int64)
        inside = (row >= 0) & (row < n_rows) & (col >= 0) & (col < n_cols)
        height = band[np.clip(row, 0, n_rows - 1), np.clip(col, 0, n_cols - 1)]
        blocked = inside & (height >= se.required_height_at_distance(distance, elevation_deg))
        if nodata is not None:
            blocked &= height != nodata
        shadow |= blocked
        distance += step_m
    return shadow


def pixel_centres_3035(bounds, width):
    lon_min, lat_min, lon_max, lat_max = bounds
    height = round(width * (lat_max - lat_min) / (lon_max - lon_min))
    lons = lon_min + (np.arange(width) + 0.5) / width * (lon_max - lon_min)
    lats = lat_max - (np.arange(height) + 0.5) / height * (lat_max - lat_min)
    lon_g, lat_g = np.meshgrid(lons, lats)
    x, y = se.WGS84_TO_RASTER_CRS.transform(lon_g, lat_g)
    return np.asarray(x), np.asarray(y)


def mask_to_png(mask: np.ndarray, path: Path) -> None:
    img = Image.fromarray(mask.astype(np.uint8), "P")  # 0 = clear, 1 = shadow
    img.putpalette([0, 0, 0, *SHADOW_RGBA[:3]] + [0] * (768 - 6))
    img.save(path, optimize=True, transparency=bytes([0, SHADOW_RGBA[3]]))


def main() -> None:
    bounds = json.loads(MAIN_JSON.read_text())["bounds"]
    xs, ys = pixel_centres_3035(bounds, GRID_W)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with rasterio.open(se.HEIGHT_RASTER) as raster:
        band = raster.read(1)
        nodata = raster.nodata
        valid = band if nodata is None else band[band != nodata]
        max_height = float(valid.max())
        for hour in HOURS:
            dt_local = datetime.datetime.combine(se.STUDY_DATE, datetime.time(hour, 0), tzinfo=se.CEST)
            azimuth, elevation = se.solar_position(dt_local)
            radius = se.search_radius_for(elevation, max_height)
            mask = shadow_mask(band, raster.transform, nodata, xs, ys, azimuth, elevation, radius)
            path = OUTPUT_DIR / shadow_file(hour)
            mask_to_png(mask, path)
            print(f"{hour}:00 az {azimuth:.1f} el {elevation:.1f} radius {radius:.0f} m: "
                  f"{100 * mask.mean():.1f}% shaded -> {path.name} ({path.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
