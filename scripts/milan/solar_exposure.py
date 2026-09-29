"""Compute sun exposure per Milan bus stop, for the critical hours of the
hottest day of documented summer 2026 (June 28 — see
docs/MILAN_DATA_DECISIONS.md for why this date and this window).

The window is 13:00-19:00 CEST (UTC+2). The ARPA dataset stamps hours in
solar time (UTC+1), so its empirical critical window 12-18 is 13-19 CEST
(see arpa_solar_to_cest()). All hours in this module are CEST.

Three signals are combined:
  - building shadow: a raster-based march toward the sun's position over the
    Copernicus Urban Atlas Building Height 2012 raster (10m, EPSG:3035)
  - tree shadow (T15): municipal trees (ds2484 census) modelled as vertical
    cylinders (radius = crown_diameter/2, from height*CROWN_BASE_FRACTION up
    to height). A stop not already in building shadow is `in_tree_shadow` if
    the ray stop -> sun crosses at least one cylinder.
  - stop shelter: the OSM `shelter` tag on the stop itself

A stop is "exposed" at a given hour if it is NOT in building shadow AND NOT
in tree shadow AND has no shelter.

Tree validity thresholds (TREE_*) are the same as in
models/staging/milan/stg_milan_trees.sql (is_valid): keep them in sync.
Besides the exposure seed, a small seed stop_tree_shade.csv records, for each
(stop, hour) in tree shadow, the nearest tree that casts it.

Search radius: the shadow march is not capped at a fixed distance. For each
hour the radius is max_raster_height / tan(elevation), rounded up to the next
STEP_M (see search_radius_for()). No building in the raster can cast a shadow
farther than that, so no shadow is missed by truncation. The radius used is
printed for every hour computed.
"""

import csv
import gzip
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
TREES_SEED = PROJECT_ROOT / "data_milan/seeds/trees/alberi_milano_20250331.csv.gz"
TREE_SHADE_CSV = PROJECT_ROOT / "data_milan/seeds/stop_tree_shade.csv"

# Tree plausibility thresholds: same as stg_milan_trees.is_valid.
TREE_HEIGHT_RANGE_M = (1.0, 45.0)
TREE_CROWN_RANGE_M = (0.5, 30.0)
CROWN_BASE_FRACTION = 1 / 3  # crown starts at this fraction of tree height

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


def load_trees(path: Path = TREES_SEED) -> dict[str, np.ndarray]:
    """Valid trees (same filters as stg_milan_trees), projected to EPSG:3035.
    Returns arrays x, y, radius, base, top and ids (object array of str).
    """
    ids, h, cd, lon, lat = [], [], [], [], []
    with gzip.open(path, "rt", newline="") as f:
        for r in csv.DictReader(f):
            try:
                hh, cc = float(r["height_m"]), float(r["crown_diameter_m"])
                lo, la = float(r["lon"]), float(r["lat"])
            except ValueError:
                continue  # missing height / crown / coordinate
            if not (TREE_HEIGHT_RANGE_M[0] <= hh <= TREE_HEIGHT_RANGE_M[1]):
                continue
            if not (TREE_CROWN_RANGE_M[0] <= cc <= TREE_CROWN_RANGE_M[1]):
                continue
            ids.append(r["tree_id"])
            h.append(hh)
            cd.append(cc)
            lon.append(lo)
            lat.append(la)
    x, y = WGS84_TO_RASTER_CRS.transform(np.array(lon), np.array(lat))
    h = np.array(h)
    return {
        "id": np.array(ids, dtype=object),
        "x": np.asarray(x),
        "y": np.asarray(y),
        "radius": np.array(cd) / 2,
        "base": h * CROWN_BASE_FRACTION,
        "top": h,
    }


class TreeIndex:
    """Uniform grid over tree centres (numpy only). Cell size = query radius,
    so a query looks at the 3x3 neighbouring cells."""

    def __init__(self, trees: dict[str, np.ndarray], cell_m: float):
        self.trees = trees
        self.cell = cell_m
        cx = np.floor(trees["x"] / cell_m).astype(np.int64)
        cy = np.floor(trees["y"] / cell_m).astype(np.int64)
        keys = cx * 1_000_003 + cy
        order = np.argsort(keys, kind="stable")
        sk = keys[order]
        uniq, start = np.unique(sk, return_index=True)
        end = np.append(start[1:], len(sk))
        self.cells = {int(k): order[a:b] for k, a, b in zip(uniq, start, end)}

    def candidates(self, x: float, y: float) -> np.ndarray:
        cx, cy = int(math.floor(x / self.cell)), int(math.floor(y / self.cell))
        parts = [
            self.cells[k]
            for dx in (-1, 0, 1)
            for dy in (-1, 0, 1)
            if (k := (cx + dx) * 1_000_003 + (cy + dy)) in self.cells
        ]
        return np.concatenate(parts) if parts else np.empty(0, dtype=np.int64)


def tree_shadow_source(
    stop_x: float,
    stop_y: float,
    azimuth_deg: float,
    elevation_deg: float,
    index: TreeIndex,
    search_radius_m: float,
):
    """Index (into the tree arrays) of the nearest tree whose crown cylinder is
    crossed by the ray stop -> sun, or None. Ray horizontal direction d, height
    at distance t is t*tan(elevation). The ray is inside a cylinder's circle for
    t in [t0-half, t0+half] (t0 = projection of the centre on d); it crosses the
    cylinder if the ray heights over that interval (clipped to t >= 0) overlap
    [base, top].
    """
    if elevation_deg <= 0:
        return None
    tr = index.trees
    idx = index.candidates(stop_x, stop_y)
    if idx.size == 0:
        return None
    az = math.radians(azimuth_deg)
    dx, dy = math.sin(az), math.cos(az)
    tan_e = math.tan(math.radians(elevation_deg))
    cx = tr["x"][idx] - stop_x
    cy = tr["y"][idx] - stop_y
    r = tr["radius"][idx]
    t0 = cx * dx + cy * dy
    perp2 = cx * cx + cy * cy - t0 * t0
    inside = perp2 <= r * r
    half = np.sqrt(np.where(inside, r * r - perp2, 0.0))
    t_lo = np.maximum(t0 - half, 0.0)
    t_hi = t0 + half
    hit = (
        inside
        & (t_hi > 0)
        & (t_lo <= search_radius_m)
        & (t_lo * tan_e <= tr["top"][idx])
        & (t_hi * tan_e >= tr["base"][idx])
    )
    if not hit.any():
        return None
    cand = np.flatnonzero(hit)
    return int(idx[cand[np.argmin(t_lo[cand])]])


def is_in_tree_shadow(*args, **kwargs) -> bool:
    return tree_shadow_source(*args, **kwargs) is not None


def main() -> None:
    stops = load_stops(STOPS_GEOJSON)
    trees = load_trees()
    print(f"Loaded {len(trees['id'])} valid trees")
    max_tree_top = float(trees["top"].max())
    print(f"Loaded {len(stops)} stops ({sum(s['has_shelter'] for s in stops)} with shelter=yes)")

    with rasterio.open(HEIGHT_RASTER) as raster:
        band = raster.read(1)
        nodata = raster.nodata
        valid = band if nodata is None else band[band != nodata]
        max_height = float(valid.max())

        rows = []
        shade_rows = []
        for hour in CRITICAL_HOURS:
            dt_local = datetime.datetime.combine(STUDY_DATE, datetime.time(hour, 0), tzinfo=CEST)
            azimuth, elevation = solar_position(dt_local)
            radius = search_radius_for(elevation, max_height)

            print(
                f"{hour:02d}:00 — azimuth {azimuth:.1f}, elevation {elevation:.1f}, "
                f"search radius {radius:.0f}m (max raster height {max_height:.0f}m)"
            )

            tree_radius = max_tree_top / math.tan(math.radians(elevation))
            index = TreeIndex(trees, max(tree_radius, 1.0))

            for stop in stops:
                x, y = WGS84_TO_RASTER_CRS.transform(stop["lon"], stop["lat"])
                in_shadow = is_in_building_shadow(x, y, azimuth, elevation, raster, band, nodata, radius)
                tree_idx = None if in_shadow else tree_shadow_source(x, y, azimuth, elevation, index, tree_radius)
                in_tree = tree_idx is not None
                if in_tree:
                    shade_rows.append(
                        {"stop_id": stop["stop_id"], "hour": hour, "tree_id": trees["id"][tree_idx]}
                    )
                exposed = not in_shadow and not in_tree and not stop["has_shelter"]
                rows.append(
                    {
                        "stop_id": stop["stop_id"],
                        "hour": hour,
                        "solar_azimuth": round(azimuth, 1),
                        "solar_elevation": round(elevation, 1),
                        "in_building_shadow": in_shadow,
                        "in_tree_shadow": in_tree,
                        "has_shelter": stop["has_shelter"],
                        "exposed": exposed,
                    }
                )

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    with open(TREE_SHADE_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["stop_id", "hour", "tree_id"])
        writer.writeheader()
        writer.writerows(shade_rows)
    print(f"Wrote {len(shade_rows)} tree-shade rows to {TREE_SHADE_CSV}")

    n_exposed = sum(r["exposed"] for r in rows)
    print(f"\nWrote {len(rows)} rows to {OUTPUT_CSV}")
    print(f"{n_exposed}/{len(rows)} (stop, hour) pairs are exposed ({100 * n_exposed / len(rows):.1f}%)")


if __name__ == "__main__":
    main()
