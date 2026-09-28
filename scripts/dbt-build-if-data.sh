#!/usr/bin/env bash
# dbt build (modelli + 49 data test) solo se gtfs.duckdb contiene i dati raw.
# I feed GTFS non sono versionati: senza ingestion il build non può girare, e non è un errore del task.
cd "$(dirname "$0")/.." || exit 2
HAS_RAW=$(python3 - <<'PY' 2>/dev/null
import duckdb
con = duckdb.connect("gtfs.duckdb", read_only=True)
print(con.execute("select count(*) from information_schema.schemata where schema_name like 'raw_%'").fetchone()[0])
PY
)
if [ "${HAS_RAW:-0}" -gt 0 ]; then
  dbt build --profiles-dir .
else
  echo "SKIP dbt build: nessuno schema raw_* in gtfs.duckdb (esegui prima ingestion/load_*.py)"
fi
