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

FILES = ["stop_solar_exposure", "stop_wait_time"]


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
        con.execute(
            f"create or replace table {schema}.{name} as "
            f"select * from read_csv_auto('{path}', union_by_name=true, "
            f"types={{'stop_id': 'VARCHAR'}})"
        )
        n = con.execute(f"select count(*) from {schema}.{name}").fetchone()[0]
        print(f"{schema}.{name}: {n} rows")
    con.close()


if __name__ == "__main__":
    main()
