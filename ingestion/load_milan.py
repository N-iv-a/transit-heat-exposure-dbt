"""Load the Milan heat-exposure seed CSVs into DuckDB raw tables.

Mirrors load_gtfs.py's pattern (one schema per source), but these two CSVs
aren't a raw GTFS feed -- they're already-computed outputs of
scripts/milan/solar_exposure.py and scripts/milan/wait_time.py (see
docs/MILAN_DATA_DECISIONS.md). This script just gets them into DuckDB so dbt
can build on top of them the same way it builds on raw_emt/raw_gva.
"""

from pathlib import Path

import duckdb

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SEEDS_DIR = PROJECT_ROOT / "data_milan" / "seeds"
DB_PATH = PROJECT_ROOT / "gtfs.duckdb"

FILES = ["stop_solar_exposure", "stop_tree_shade", "stop_wait_time"]

OSM_SHELTER_PATH = SEEDS_DIR / "osm_shelter" / "export_shelter_milano.geojson"


def _load_osm_shelter_stops(con: duckdb.DuckDBPyConnection, schema: str) -> None:
    if not OSM_SHELTER_PATH.exists():
        raise FileNotFoundError(f"Missing {OSM_SHELTER_PATH}")
    # GeoJSON FeatureCollection: one row per feature after unnesting.
    # ref/name are cast to VARCHAR -- ref is not always numeric (e.g. GTFS's
    # own "ABBIATEGRASSO" stop_id, see stop_wait_time.csv). geometry.coordinates
    # is [lon, lat] per the GeoJSON spec; DuckDB list indexing is 1-based, so
    # coordinates[1] is lon and coordinates[2] is lat.
    con.execute(
        f"""
        create or replace table {schema}.osm_shelter_stops as
        select
            f.id as osm_node_id,
            cast(f.properties.ref as varchar) as ref,
            cast(f.properties.name as varchar) as name,
            cast(f.geometry.coordinates[1] as double) as lon,
            cast(f.geometry.coordinates[2] as double) as lat
        from (
            select unnest(features) as f
            from read_json_auto('{OSM_SHELTER_PATH}')
        )
        """
    )
    n = con.execute(f"select count(*) from {schema}.osm_shelter_stops").fetchone()[0]
    print(f"{schema}.osm_shelter_stops: {n} rows")


TREES_PATH = SEEDS_DIR / "trees" / "alberi_milano_20250331.csv.gz"


def _load_trees(con: duckdb.DuckDBPyConnection, schema: str) -> None:
    if not TREES_PATH.exists():
        raise FileNotFoundError(
            f"Missing {TREES_PATH} -- run scripts/milan/prepare_tree_seed.py (needs the raw ds2484 CSV)."
        )
    con.execute(
        f"""
        create or replace table {schema}.trees as
        select * from read_csv('{TREES_PATH}', header=true,
            types={{'tree_id': 'VARCHAR', 'genus': 'VARCHAR', 'species': 'VARCHAR',
                    'height_m': 'DOUBLE', 'crown_diameter_m': 'DOUBLE',
                    'lon': 'DOUBLE', 'lat': 'DOUBLE'}})
        """
    )
    n = con.execute(f"select count(*) from {schema}.trees").fetchone()[0]
    print(f"{schema}.trees: {n} rows")


def main() -> None:
    con = duckdb.connect(str(DB_PATH))
    schema = "raw_milan"
    con.execute(f"create schema if not exists {schema}")
    for name in FILES:
        path = SEEDS_DIR / f"{name}.csv"
        if not path.exists():
            raise FileNotFoundError(
                f"Missing {path} -- run scripts/milan/solar_exposure.py and "
                f"scripts/milan/wait_time.py first (see scripts/milan/README.md)."
            )
        # stop_wait_time.csv has one data-quality row (stop_id="ABBIATEGRASSO",
        # from wait_time.py's own source data) that breaks BIGINT
        # auto-detection -- same fix applied there, needed again here.
        types = "'stop_id': 'VARCHAR'" + (", 'tree_id': 'VARCHAR'" if name == "stop_tree_shade" else "")
        con.execute(
            f"create or replace table {schema}.{name} as "
            f"select * from read_csv_auto('{path}', union_by_name=true, "
            f"types={{{types}}})"
        )
        n = con.execute(f"select count(*) from {schema}.{name}").fetchone()[0]
        print(f"{schema}.{name}: {n} rows")
    _load_osm_shelter_stops(con, schema)
    _load_trees(con, schema)
    con.close()


if __name__ == "__main__":
    main()
