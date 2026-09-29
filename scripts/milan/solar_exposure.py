"""Compute sun exposure per Milan bus stop, for the critical hours of the
hottest day of documented summer 2026 (June 28 — see
docs/MILAN_DATA_DECISIONS.md for why this date and this window).

The window is 13:00-19:00 CEST (UTC+2). The ARPA dataset stamps hours in
solar time (UTC+1), so its empirical critical window 12-18 is 13-19 CEST
(see arpa_solar_to_cest()). All hours in this module are CEST.

Two signals are combined:
  - building shadow: a raster-based march toward the sun's position over the
    Copernicus Urban Atlas Building Height 2012 raster (10m, EPSG:3035)
  - stop shelter: the OSM `shelter` tag on the stop itself

A stop is "exposed" at a given hour if it is NOT in building shadow AND has
no shelter.

Search radius: the shadow march is not capped at a fixed distance. For each
hour the radius is max_raster_height / tan(elevation), rounded up to the next
STEP_M (see search_radius_for()). No building in the raster can cast a shadow
farther than that, so no shadow is missed by truncation. The radius used is
printed for every hour computed.
"""

import csv
import datetime
import math
from pathlib import Path

import numpy as np
import rasterio
from pyproj import Transformer
from pysolar.solar import get_altitude, get_azimuth

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
HEIGHT_RASTER = PROJECT_ROOT / "data_milan/seeds/building_height/IT002_MILANO_UA2012_DHM_V010.tif"
STOPS_GEOJSON = PROJECT_ROOT / "data_milan/seeds/osm_shelter/export_shelter_milano.geojson"
OUTPUT_CSV = PROJECT_ROOT / "data_milan/seeds/stop_solar_exposure.csv"

MILAN_LAT, MILAN_LON = 45.4642, 9.1900
STUDY_DATE = datetime.date(2026, 6, 28)  # hottest day found in the ARPA analysis
CEST = datetime.timezone(datetime.timedelta(hours=2))
CRITICAL_HOURS = range(13, 20)  # 13:00-19:00 CEST, inclusive (= ARPA 12-18 solar time)
ARPA_SOLAR_UTC_OFFSET = datetime.timedelta(hours=1)
CEST_UTC_OFFSET = datetime.timedelta(hours=2)

STEP_M = 10  # matches raster resolution; no point stepping finer than a pixel

WGS84_TO_RASTER_CRS = Transformer.from_crs("EPSG:4326", "EPSG:3035", always_xy=True)


def load_stops(path: Path) -> list[dict]:
    import json

    with open(path) as f:
        data = json.load(f)

    stops = []
    for feat in data["features"]:
        props = feat["properties"]
        lon, lat = feat["geometry"]["coordinates"]
        stops.append(
            {
                "stop_id": props["@id"],
                "name": props.get("name", ""),
                "lon": lon,
                "lat": lat,
                "has_shelter": props.get("shelter") == "yes",
            }
        )
    return stops


def arpa_solar_to_cest(dt_naive: datetime.datetime) -> datetime.datetime:
    """ARPA timestamps are in solar time (UTC+1); convert a naive ARPA
    datetime to naive CEST (UTC+2), i.e. add one hour.
    """
    return dt_naive + (CEST_UTC_OFFSET - ARPA_SOLAR_UTC_OFFSET)


def solar_position(dt_local: datetime.datetime) -> tuple[float, float]:
    """Returns (azimuth_deg, elevation_deg) for Milan at the given local time."""
    dt_utc = dt_local.astimezone(datetime.timezone.utc)
    elevation = get_altitude(MILAN_LAT, MILAN_LON, dt_utc)
    azimuth = get_azimuth(MILAN_LAT, MILAN_LON, dt_utc)
    return azimuth, elevation


def required_height_at_distance(distance_m: float, elevation_deg: float) -> float:
    """Minimum building height at `distance_m` needed to cast a shadow this far."""
    return distance_m * math.tan(math.radians(elevation_deg))


def search_radius_for(elevation_deg: float, max_height_m: float, step_m: float = STEP_M) -> float:
    """Distance beyond which no building of height <= max_height_m can shade a
    stop with the sun at `elevation_deg`, rounded up to a multiple of step_m.
    """
    if elevation_deg <= 0:
        raise ValueError("sun below the horizon: no finite search radius")
    return math.ceil(max_height_m / math.tan(math.radians(elevation_deg)) / step_m) * step_m


def is_in_building_shadow(
    stop_x: float,
    stop_y: float,
    azimuth_deg: float,
    elevation_deg: float,
    raster,
    band: np.ndarray,
    nodata: float,
    search_radius_m: float,
    step_m: float = STEP_M,
) -> bool:
    """March from the stop toward the sun's azimuth, checking whether any
    building along the way is tall enough to cast a shadow back to the stop.
    """
    az_rad = math.radians(azimuth_deg)
    dx, dy = math.sin(az_rad), math.cos(az_rad)  # bearing -> (easting, northing)

    distance = step_m
    while distance <= search_radius_m:
        x = stop_x + distance * dx
        y = stop_y + distance * dy
        row, col = raster.index(x, y)
        if 0 <= row < band.shape[0] and 0 <= col < band.shape[1]:
            height = band[row, col]
            if height != nodata and height >= required_height_at_distance(distance, elevation_deg):
                return True
        distance += step_m
    return False


def main() -> None:
    stops = load_stops(STOPS_GEOJSON)
    print(f"Loaded {len(stops)} stops ({sum(s['has_shelter'] for s in stops)} with shelter=yes)")

    with rasterio.open(HEIGHT_RASTER) as raster:
        band = raster.read(1)
        nodata = raster.nodata
        valid = band if nodata is None else band[band != nodata]
        max_height = float(valid.max())

        rows = []
        for hour in CRITICAL_HOURS:
            dt_local = datetime.datetime.combine(STUDY_DATE, datetime.time(hour, 0), tzinfo=CEST)
            azimuth, elevation = solar_position(dt_local)
            radius = search_radius_for(elevation, max_height)

            print(
                f"{hour:02d}:00 — azimuth {azimuth:.1f}, elevation {elevation:.1f}, "
                f"search radius {radius:.0f}m (max raster height {max_height:.0f}m)"
            )

            for stop in stops:
                x, y = WGS84_TO_RASTER_CRS.transform(stop["lon"], stop["lat"])
                in_shadow = is_in_building_shadow(x, y, azimuth, elevation, raster, band, nodata, radius)
                exposed = not in_shadow and not stop["has_shelter"]
                rows.append(
                    {
                        "stop_id": stop["stop_id"],
                        "hour": hour,
                        "solar_azimuth": round(azimuth, 1),
                        "solar_elevation": round(elevation, 1),
                        "in_building_shadow": in_shadow,
                        "has_shelter": stop["has_shelter"],
                        "exposed": exposed,
                    }
                )

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    n_exposed = sum(r["exposed"] for r in rows)
    print(f"\nWrote {len(rows)} rows to {OUTPUT_CSV}")
    print(f"{n_exposed}/{len(rows)} (stop, hour) pairs are exposed ({100 * n_exposed / len(rows):.1f}%)")


if __name__ == "__main__":
    main()
