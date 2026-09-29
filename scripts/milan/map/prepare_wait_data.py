"""Read main.int_stop_wait_time from gtfs.duckdb into the compact per-stop
JSON the map template embeds (id, n(ame), lo(n), la(t), w(ait minutes per
hour, 12..18, null where the stop has no service that hour), nl (lines
observed per hour)). Output format unchanged from the CSV-based version.
"""

import json
from collections import defaultdict
from pathlib import Path

import duckdb

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DUCKDB_PATH = PROJECT_ROOT / "gtfs.duckdb"
OUTPUT_JSON = Path(__file__).resolve().parent / "data" / "wait_time.json"

HOURS = range(12, 19)

QUERY = """
select gtfs_stop_id, stop_name, lon, lat, hour, median_wait_minutes, n_lines
from main.int_stop_wait_time
"""


def main() -> None:
    con = duckdb.connect(str(DUCKDB_PATH), read_only=True)
    rows = con.execute(QUERY).fetchall()
    con.close()

    by_stop = defaultdict(dict)
    meta = {}
    for stop_id, stop_name, lon, lat, hour, median_wait_minutes, n_lines in rows:
        by_stop[stop_id][hour] = (median_wait_minutes, n_lines)
        meta[stop_id] = (stop_name, lon, lat)

    records = []
    for stop_id, hours in by_stop.items():
        name, lon, lat = meta[stop_id]
        w, nl = [], []
        for h in HOURS:
            if h in hours:
                w.append(round(hours[h][0], 2) if hours[h][0] is not None else None)
                nl.append(hours[h][1])
            else:
                w.append(None)
                nl.append(0)
        records.append(
            {"id": stop_id, "n": name, "lo": round(lon, 5), "la": round(lat, 5), "w": w, "nl": nl}
        )

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w") as f:
        json.dump(records, f, separators=(",", ":"))

    print(f"Wrote {len(records)} stops to {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
