# Transit Heat Exposure: fonte di verità

Obiettivo, architettura, modello dati, contratto, decisioni. Gli agent la leggono quando pianificano; tienila corta e aggiornata.

## Obiettivo
Modellare feed GTFS reali in uno star schema testato (dbt + DuckDB), una città alla volta, e rispondere a domande oltre il GTFS (Milano: esposizione al sole e attesa alla fermata).

## Architettura
`raw_<fonte>.*` (ingestion) → `staging/<fonte>/` → `intermediate/` → `marts/`. Un solo progetto dbt, un solo `gtfs.duckdb`. Aggiungere una città = schema `raw_<città>`, cartella `staging/<città>/`, doc `docs/<CITTÀ>_DATA_DECISIONS.md`.

## Modello dati e decisioni
- Mappa generale: `README.md`.
- Valencia (EMT + GVA, chiavi con prefisso agenzia): `docs/VALENCIA_DATA_DECISIONS.md`.
- Milano (esposizione solare, rischio calore, tempi d'attesa, tool mappa): `docs/MILAN_DATA_DECISIONS.md`.

## Contratto
Nessun contratto formale in `contract/`. La mappa (`scripts/milan/map/`) legge i seed `data_milan/seeds/stop_solar_exposure.csv`, `stop_wait_time.csv` e l'export OSM: cambiarne le colonne è una modifica di contratto.
Fermate OSM (esposizione) e GTFS (attesa) sono collegate in dbt da `int_osm_gtfs_stop_bridge` (prima `ref` OSM, poi fermata più vicina entro 30 m); vista combinata in `mart_stop_heat_wait`.
