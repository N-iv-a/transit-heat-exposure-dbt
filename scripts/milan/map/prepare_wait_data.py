"""Read main.int_stop_wait_time from gtfs.duckdb into the compact per-stop
JSON the map template embeds (id, n(ame), lo(n), la(t), w(ait minutes per
hour, 13..19, = wait_mixed_minutes, null where the stop has no service that
hour), nd (n_departures per hour), wl/wh (low = min(wait_any_line_minutes, wait_mixed_minutes), high =
wait_least_frequent_minutes), nl (lines observed per hour)).
"""

import json
from collections import defaultdict
from pathlib import Path

import duckdb

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DUCKDB_PATH = PROJECT_ROOT / "gtfs.duckdb"
OUTPUT_JSON = Path(__file__).resolve().parent / "data" / "wait_time.json"

HOURS = range(13, 20)

QUERY = """
select gtfs_stop_id, stop_name, lon, lat, hour, wait_mixed_minutes,
       wait_any_line_minutes, wait_least_frequent_minutes, n_lines, n_departures
from main.int_stop_wait_time
"""


def _r(v):
    return round(v, 1) if v is not None else None


def main() -> None:
    con = duckdb.connect(str(DUCKDB_PATH), read_only=True)
    rows = con.execute(QUERY).fetchall()
    con.close()

    by_stop = defaultdict(dict)
    meta = {}
    for stop_id, stop_name, lon, lat, hour, mixed, low, high, n_lines, n_dep in rows:
        by_stop[stop_id][hour] = (mixed, low, high, n_lines, n_dep)
        meta[stop_id] = (stop_name, lon, lat)

    records = []
    for stop_id, hours in by_stop.items():
        name, lon, lat = meta[stop_id]
        w, wl, wh, nl, nd = [], [], [], [], []
        for h in HOURS:
            m, lo_, hi_, n, dep = hours.get(h, (None, None, None, 0, 0))
            w.append(_r(m))
            # same definition as the mart's wait_minutes_low: min(any-line, central)
            wl.append(_r(min(lo_, m)) if m is not None and lo_ is not None else _r(lo_))
            wh.append(_r(hi_))
            nl.append(n)
            nd.append(dep)
        records.append(
            {"id": stop_id, "n": name, "lo": round(lon, 5), "la": round(lat, 5),
             "w": w, "wl": wl, "wh": wh, "nl": nl, "nd": nd}
        )

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w") as f:
        json.dump(records, f, separators=(",", ":"))

    print(f"Wrote {len(records)} stops to {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
