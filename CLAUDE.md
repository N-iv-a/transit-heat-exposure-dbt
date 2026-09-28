# Transit Heat Exposure — GTFS + dbt

Feed GTFS reali (Valencia EMT/GVA, Milano ATM) modellati con dbt + DuckDB in uno star schema testato, esteso città per città.

## Architettura
Nessun server né cloud warehouse: tutto gira su un file locale `gtfs.duckdb`.
- **backend** (dati): `ingestion/load_*.py` (CSV → schemi `raw_*`) → dbt `models/` staging → intermediate → marts, con data test in `tests/`. Script Python di Milano in `scripts/milan/` (esposizione solare, tempi di attesa).
- **frontend**: il tool mappa `scripts/milan/map/` (template HTML + script di preparazione dati → `dist/milan_heat_map.html` autocontenuto).
- **contratto**: `contract/` (vuoto finché non serve); di fatto l'interfaccia verso la mappa sono i seed in `data_milan/seeds/`.

La fonte di verità per cartelle e comandi è `.claude/loop.json` → `paths` e `docs.source`.

## Comandi
Tutti in `.claude/loop.json → commands`. Eseguili con `scripts/loop/check.sh <lint|build|test|e2e|all> <backend|frontend>`, non a mano: l'output viene tagliato e il log salvato in `.claude/run/`.
- backend: lint `dbt parse` + `py_compile`, build `dbt compile`, test `pytest scripts/milan` + `dbt build` solo se `gtfs.duckdb` ha i dati raw (`scripts/dbt-build-if-data.sh`).
- frontend: build della mappa dai seed versionati, test = HTML generato senza segnaposto rimasti. Nessun e2e.
- Dipendenze: `requirements.txt` (dbt) e `scripts/milan/requirements.txt` (Milano). I feed GTFS non sono versionati: vedi `docs/*_DATA_DECISIONS.md`.

## Regole
- Solo dati fittizi nel codice e nei test; i dati veri (feed GTFS, open data) entrano solo da ingestion/seed documentati.
- Fonte di verità: `docs/spec.md`, che rimanda a `docs/VALENCIA_DATA_DECISIONS.md` e `docs/MILAN_DATA_DECISIONS.md`.
- Commit solo con `scripts/loop/commit.sh` (conventional commits).
- Flusso di lavoro: skill `dev-loop` (guida in `docs/DEV_LOOP.md`). Livelli: `scripts/loop/level.sh`.
- Dopo aver toccato hook, pattern o allowlist: `scripts/tests/test-hooks.sh` deve dire «0 falliti».
