"""Read main.mart_trees_map from gtfs.duckdb into a columnar, quantized JSON
(`data/trees.json`) that the map's "Trees" view loads on demand.

Format (one entry per tree, all arrays the same length n; the trees are sorted
in row bands of ~2 km and by x inside a band, then position columns are
delta-encoded, which makes the file ~3x smaller after gzip):
    lon0, lat0, scale   origin (deg) and step (deg per unit) of the grid
    x, y                grid position, delta-encoded: x[0] absolute, then
                        x[i] - x[i-1]; lon = lon0 + cumsum(x) * scale
    h                   height, whole meters
    c                   crown diameter, units of 0.5 m
    sp                  index into `species`
    species             [[genus index, species name], ...]
    genera              [genus, ...]
    s                   indices of the trees whose crown shades a stop
                        (mart_trees_map.shades_stop)
    n                   number of trees
Optional `partial: true` + `total` are added by build_map.py when the
single-file build inlines only the shading trees.

The grid step is 1e-5 deg (about 0.8-1.1 m), finer than the census positions.
"""

import json
from pathlib import Path

import duckdb

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DUCKDB_PATH = PROJECT_ROOT / "gtfs.duckdb"
OUTPUT_JSON = Path(__file__).resolve().parent / "data" / "trees.json"

SCALE = 1e-5
BAND = 200  # grid units (~2 km of latitude) per sorting band

QUERY = """
select genus, species, height_m, crown_diameter_m, lon, lat, shades_stop
from main.mart_trees_map
"""


def delta(values: list[int]) -> list[int]:
    return values[:1] + [values[i] - values[i - 1] for i in range(1, len(values))]


def undelta(values: list[int]) -> list[int]:
    out, acc = [], 0
    for v in values:
        acc += v
        out.append(acc)
    return out


def encode(rows, lon0: float, lat0: float) -> dict:
    """rows: (genus, species, height_m, crown_m, lon, lat, shades_stop)."""
    recs = sorted(
        (
            (round((r[5] - lat0) / SCALE) // BAND, round((r[4] - lon0) / SCALE), round((r[5] - lat0) / SCALE), r)
            for r in rows
        ),
        key=lambda t: (t[0], t[1], t[2]),
    )
    genera: dict[str, int] = {}
    species: dict[tuple[int, str], int] = {}
    x, y, h, c, sp, s = [], [], [], [], [], []
    for i, (_, gx, gy, r) in enumerate(recs):
        g = genera.setdefault(r[0] or "", len(genera))
        k = species.setdefault((g, r[1] or ""), len(species))
        x.append(gx)
        y.append(gy)
        h.append(round(r[2]))
        c.append(round(r[3] * 2))
        sp.append(k)
        if r[6]:
            s.append(i)
    return {
        "lon0": round(lon0, 6),
        "lat0": round(lat0, 6),
        "scale": SCALE,
        "n": len(recs),
        "x": delta(x),
        "y": delta(y),
        "h": h,
        "c": c,
        "sp": sp,
        "species": [[g, name] for (g, name) in species],
        "genera": list(genera),
        "s": s,
    }


def main() -> None:
    con = duckdb.connect(str(DUCKDB_PATH), read_only=True)
    rows = con.execute(QUERY).fetchall()
    con.close()
    lon0 = min(r[4] for r in rows)
    lat0 = min(r[5] for r in rows)
    payload = encode(rows, lon0, lat0)
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w") as f:
        json.dump(payload, f, separators=(",", ":"), ensure_ascii=False)
    print(
        f"Wrote {payload['n']} trees ({len(payload['s'])} shade a stop) to {OUTPUT_JSON} "
        f"({OUTPUT_JSON.stat().st_size / 1024:.0f} KB)"
    )


if __name__ == "__main__":
    main()
