"""Read the shelter flag of every OSM stop from main.mart_stop_heat_wait_hourly
into data/exposure.json: a compact list of the ids (osm node number, same `id`
as data/main.json) of the stops that have a shelter. The page only uses it for
the "Has shelter" line of the stop tooltip: exposure scores themselves come
from data/main.json (one source, same values in every view).

See contract/map_data.md -- the frontend does not recompute exposure_score.
"""

import json
from pathlib import Path

import duckdb

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DUCKDB_PATH = PROJECT_ROOT / "gtfs.duckdb"
OUTPUT_JSON = Path(__file__).resolve().parent / "data" / "exposure.json"

QUERY = """
select distinct osm_node_id
from main.mart_stop_heat_wait_hourly
where has_shelter
order by osm_node_id
"""


def main() -> None:
    con = duckdb.connect(str(DUCKDB_PATH), read_only=True)
    ids = [r[0].replace("node/", "") for r in con.execute(QUERY).fetchall()]
    con.close()

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w") as f:
        json.dump(ids, f, separators=(",", ":"))

    print(f"Wrote {len(ids)} sheltered stop ids to {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
