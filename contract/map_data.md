# Contratto dbt → mappa Milano

La mappa (`scripts/milan/map/`) legge da `gtfs.duckdb` dopo il build dbt dei modelli di Milano, non più dai CSV dei seed. Il backend garantisce queste tabelle e colonne; il frontend non ricalcola nulla di ciò che è qui.

Ordine di build: `python3 ingestion/load_milan.py` → `dbt run --select source:raw_milan+` → script `prepare_*` della mappa → `build_map.py`. Funziona offline: i seed di Milano sono versionati.

## `main.mart_stop_heat_wait_hourly` — vista principale e vista esposizione
Grain: una riga per (`osm_node_id`, `hour`), 2.931 fermate × 7 ore = 20.517 righe.

| Colonna | Tipo | Note |
|---|---|---|
| `osm_node_id` | VARCHAR | `node/N`, non nullo |
| `stop_name` | VARCHAR | nome OSM, può essere vuoto |
| `lon`, `lat` | DOUBLE | coordinate OSM della fermata (WGS84) |
| `hour` | INTEGER | 12–18 |
| `in_building_shadow` | BOOLEAN | |
| `has_shelter` | BOOLEAN | |
| `exposure_score` | DOUBLE | 0 ombra edificio, `shelter_exposure_factor` (0,5) sole con pensilina, 1 sole senza pensilina |
| `gtfs_stop_id` | VARCHAR | NULL se non abbinata |
| `match_method` | VARCHAR | `ref`, `nearest`, `unmatched` |
| `wait_minutes` | DOUBLE | attesa mediana a quell'ora; NULL se non abbinata o senza servizio in quell'ora |
| `exposed_wait_minutes` | DOUBLE | `exposure_score × wait_minutes`; NULL se `wait_minutes` è NULL |
| `risk_level` | VARCHAR | della fermata (non dell'ora): `low`, `medium`, `high` |

## `main.int_stop_wait_time` — vista attesa
Invariata: una riga per (`gtfs_stop_id`, `hour`) con `stop_name`, `lat`, `lon`, `median_wait_minutes`, `n_lines`, `wait_time_bucket`.

## Codifica visiva concordata (vista principale)
- Una colonna 3D per fermata OSM, per l'ora selezionata o la media 12–18.
- Altezza = `wait_minutes`, tetto a 25 min.
- Colore = `exposure_score`: ombra / pensilina al sole / sole pieno.
- Fermate con `wait_minutes` NULL: punto grigio a terra, senza colonna.
