"""Load extracted GTFS .txt files into DuckDB raw tables, one schema per agency.

Expects data/raw/<agency>/*.txt to already exist (see README for how to get the
feeds — the ingestion step itself is source-agnostic, it just points at a
local directory of GTFS text files).
"""

from pathlib import Path

import duckdb

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
DB_PATH = PROJECT_ROOT / "gtfs.duckdb"

# shapes.txt and feed_info.txt are not loaded: neither is used by any model
# in this project (no route-shape geometry or feed-metadata analysis here).
AGENCY_FILES = {
    "emt": ["agency", "routes", "trips", "stops", "stop_times", "calendar", "calendar_dates"],
    "gva": ["agency", "routes", "trips", "stops", "stop_times", "calendar_dates"],
}


def main() -> None:
    con = duckdb.connect(str(DB_PATH))
    for agency, files in AGENCY_FILES.items():
        schema = f"raw_{agency}"
        con.execute(f"create schema if not exists {schema}")
        for name in files:
            path = RAW_DIR / agency / f"{name}.txt"
            if not path.exists():
                raise FileNotFoundError(
                    f"Missing {path} — download the {agency.upper()} GTFS feed and "
                    f"extract it to data/raw/{agency}/ first (see README)."
                )
            con.execute(
                f"create or replace table {schema}.{name} as "
                f"select * from read_csv_auto('{path}', union_by_name=true)"
            )
            n = con.execute(f"select count(*) from {schema}.{name}").fetchone()[0]
            print(f"{schema}.{name}: {n} rows")
    con.close()


if __name__ == "__main__":
    main()
