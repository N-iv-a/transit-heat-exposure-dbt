"""Aggregate stop_wait_time.csv into the compact per-stop JSON the map
template embeds (id, n(ame), lo(n), la(t), w(ait minutes per hour, 12..18,
null where the stop has no service that hour), nl (lines observed per hour)).
"""

import json
from collections import defaultdict
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
WAIT_CSV = PROJECT_ROOT / "data_milan/seeds/stop_wait_time.csv"
OUTPUT_JSON = Path(__file__).resolve().parent / "data" / "wait_time.json"

HOURS = range(12, 19)


def main() -> None:
    df = pd.read_csv(WAIT_CSV)

    by_stop = defaultdict(dict)
    meta = {}
    for row in df.itertuples():
        by_stop[row.stop_id][row.hour] = (row.median_wait_minutes, row.n_lines)
        meta[row.stop_id] = (row.stop_name, row.lon, row.lat)

    records = []
    for stop_id, hours in by_stop.items():
        name, lon, lat = meta[stop_id]
        w, nl = [], []
        for h in HOURS:
            if h in hours:
                w.append(hours[h][0])
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
