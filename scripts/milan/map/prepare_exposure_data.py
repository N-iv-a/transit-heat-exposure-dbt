"""Read main.mart_stop_heat_wait_hourly from gtfs.duckdb into the compact
per-stop JSON the map template embeds directly (field names kept short since
this ships inline in the page: id, n(ame), lo(n), la(t), sh(elter),
e(xposure score summed 13..19, 0-7), h(ourly exposure_score, 13..19)).

See contract/map_data.md for the mart's grain and columns -- the frontend
does not recompute exposure_score, it only aggregates per stop for display.
"""

import json
from pathlib import Path

import duckdb

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DUCKDB_PATH = PROJECT_ROOT / "gtfs.duckdb"
OUTPUT_JSON = Path(__file__).resolve().parent / "data" / "exposure.json"

HOURS = list(range(13, 20))

QUERY = """
select osm_node_id, stop_name, lon, lat, has_shelter, hour, exposure_score
from main.mart_stop_heat_wait_hourly
order by osm_node_id, hour
"""


def main() -> None:
    con = duckdb.connect(str(DUCKDB_PATH), read_only=True)
    rows = con.execute(QUERY).fetchall()
    con.close()

    by_stop: dict[str, dict] = {}
    for osm_node_id, stop_name, lon, lat, has_shelter, hour, exposure_score in rows:
        stop = by_stop.setdefault(
            osm_node_id,
            {"n": stop_name or "", "lo": lon, "la": lat, "sh": bool(has_shelter), "scores": {}},
        )
        stop["scores"][hour] = exposure_score

    records = []
    for osm_node_id, stop in by_stop.items():
        h = [stop["scores"].get(hr) for hr in HOURS]
        records.append(
            {
                "id": osm_node_id.replace("node/", ""),
                "n": stop["n"],
                "lo": round(stop["lo"], 5),
                "la": round(stop["la"], 5),
                "sh": stop["sh"],
                "e": round(sum(v for v in h if v is not None), 3),
                "h": [round(v, 3) if v is not None else None for v in h],
            }
        )

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w") as f:
        json.dump(records, f, separators=(",", ":"))

    print(f"Wrote {len(records)} stops to {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
