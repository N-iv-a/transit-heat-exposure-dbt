#!/usr/bin/env bash
# dbt build (modelli + data test) solo per le sorgenti raw_* presenti in gtfs.duckdb.
# I feed GTFS non sono versionati: senza ingestion il build non può girare, e non è un errore del task.
# Milano si carica dai seed versionati (python ingestion/load_milan.py); Valencia serve i feed in data/raw/.
cd "$(dirname "$0")/.." || exit 2
RAW=$(python3 - <<'PY' 2>/dev/null
import duckdb
con = duckdb.connect("gtfs.duckdb", read_only=True)
rows = con.execute("select distinct schema_name from information_schema.schemata where schema_name like 'raw_%' order by 1").fetchall()
print(" ".join(r[0] for r in rows))
PY
)
if [ -z "$RAW" ]; then
  echo "SKIP dbt build: nessuno schema raw_* in gtfs.duckdb (esegui prima ingestion/load_*.py)"
  exit 0
fi
SEL=""
for s in $RAW; do SEL="$SEL source:$s+"; done
echo "dbt build per:$SEL"
dbt build --profiles-dir . --indirect-selection=cautious --select $SEL
