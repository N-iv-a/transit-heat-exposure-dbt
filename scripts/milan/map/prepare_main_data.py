"""Read main.mart_stop_heat_wait_hourly from gtfs.duckdb into the compact
JSON the main deck.gl view embeds directly.

Output `data/main.json`:
    {
      "bounds": [lonMin, latMin, lonMax, latMax],
      "stops": [
        {"id": ..., "n": ..., "lo": ..., "la": ...,
         "s": [exposure_score x7, hours 13..19],
         "w": [wait_minutes (mixed model, central)|null x7, hours 13..19],
         "wl": [wait_minutes_low|null x7], "wh": [wait_minutes_high|null x7],
         "dc": exposure_decile 1..10, "st": risk_level_stable 1/0}
      ]
    }

One record per osm_node_id (the mart's grain is osm_node_id x hour). This
is the only script `render_building_backdrop.py`'s deck.gl backdrop and
`build_map.py`'s __MAIN_DATA_JSON__ placeholder depend on -- run it before
those two (see .claude/loop.json's frontend build command for the order).
"""

import json
from pathlib import Path

import duckdb

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DUCKDB_PATH = PROJECT_ROOT / "gtfs.duckdb"
OUTPUT_JSON = Path(__file__).resolve().parent / "data" / "main.json"

HOURS = list(range(13, 20))

QUERY = """
select osm_node_id, stop_name, lon, lat, hour, exposure_score, wait_minutes,
       wait_minutes_low, wait_minutes_high, exposure_decile, risk_level_stable
from main.mart_stop_heat_wait_hourly
order by osm_node_id, hour
"""


def _r(v):
    return round(v, 1) if v is not None else None


def main() -> None:
    con = duckdb.connect(str(DUCKDB_PATH), read_only=True)
    rows = con.execute(QUERY).fetchall()
    con.close()

    by_stop: dict[str, dict] = {}
    for (osm_node_id, stop_name, lon, lat, hour, exposure_score, wait_minutes,
         wait_low, wait_high, decile, stable) in rows:
        stop = by_stop.setdefault(
            osm_node_id,
            {"n": stop_name or "", "lo": lon, "la": lat, "scores": {}, "waits": {}, "lows": {}, "highs": {},
             "dc": decile, "st": stable},
        )
        stop["scores"][hour] = exposure_score
        stop["waits"][hour] = wait_minutes
        stop["lows"][hour] = wait_low
        stop["highs"][hour] = wait_high

    stops = []
    lons, lats = [], []
    for osm_node_id, stop in by_stop.items():
        lons.append(stop["lo"])
        lats.append(stop["la"])
        stops.append(
            {
                "id": osm_node_id.replace("node/", ""),
                "n": stop["n"],
                "lo": round(stop["lo"], 5),
                "la": round(stop["la"], 5),
                "s": [round(stop["scores"][hr], 3) for hr in HOURS],
                "w": [_r(stop["waits"][hr]) for hr in HOURS],
                "wl": [_r(stop["lows"][hr]) for hr in HOURS],
                "wh": [_r(stop["highs"][hr]) for hr in HOURS],
                "dc": stop["dc"],
                "st": 1 if stop["st"] else 0,
            }
        )

    bounds = [round(min(lons), 5), round(min(lats), 5), round(max(lons), 5), round(max(lats), 5)]
    payload = {"bounds": bounds, "stops": stops}

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w") as f:
        json.dump(payload, f, separators=(",", ":"))

    print(f"Wrote {len(stops)} stops to {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
