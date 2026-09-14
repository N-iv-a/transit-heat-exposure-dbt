"""Aggregate stop_solar_exposure.csv + the OSM shelter export into the
compact per-stop JSON the map template embeds directly (field names kept
short since this ships inline in the page: id, n(ame), lo(n), la(t),
sh(elter), e(xposed hour count), h(ourly exposed booleans)).
"""

import json
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
EXPOSURE_CSV = PROJECT_ROOT / "data_milan/seeds/stop_solar_exposure.csv"
SHELTER_GEOJSON = PROJECT_ROOT / "data_milan/seeds/osm_shelter/export_shelter_milano.geojson"
OUTPUT_JSON = Path(__file__).resolve().parent / "data" / "exposure.json"


def main() -> None:
    exposure = pd.read_csv(EXPOSURE_CSV)

    with open(SHELTER_GEOJSON) as f:
        stops_geo = json.load(f)

    stop_meta = {}
    for feat in stops_geo["features"]:
        props = feat["properties"]
        stop_id = props["@id"]
        lon, lat = feat["geometry"]["coordinates"]
        stop_meta[stop_id] = {
            "name": props.get("name", ""),
            "lon": lon,
            "lat": lat,
            "shelter": props.get("shelter") == "yes",
        }

    agg = exposure.groupby("stop_id").agg(exposed_hours=("exposed", "sum")).reset_index()

    records = []
    for _, row in agg.iterrows():
        meta = stop_meta.get(row["stop_id"])
        if not meta:
            continue
        hours = (
            exposure[exposure.stop_id == row["stop_id"]]
            .sort_values("hour")["exposed"]
            .astype(int)
            .tolist()
        )
        records.append(
            {
                "id": row["stop_id"].replace("node/", ""),
                "n": meta["name"],
                "lo": round(meta["lon"], 5),
                "la": round(meta["lat"], 5),
                "sh": meta["shelter"],
                "e": int(row["exposed_hours"]),
                "h": hours,
            }
        )

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w") as f:
        json.dump(records, f, separators=(",", ":"))

    print(f"Wrote {len(records)} stops to {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
