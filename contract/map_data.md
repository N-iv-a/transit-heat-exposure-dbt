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
| `hour` | INTEGER | 13–19, ora locale CEST (UTC+2) |
| `in_building_shadow` | BOOLEAN | |
| `has_shelter` | BOOLEAN | |
| `in_tree_shadow` | BOOLEAN | chioma di un albero comunale tra la fermata e il sole (T15); `false` se già in ombra di edificio |
| `exposure_score` | DOUBLE | 0 ombra edificio, `tree_transmissivity` (0,03) ombra di chioma, `shelter_exposure_factor` (0,5) sole con pensilina, 1 sole senza pensilina |
| `gtfs_stop_id` | VARCHAR | NULL se non abbinata |
| `match_method` | VARCHAR | `ref`, `nearest`, `unmatched` |
| `wait_minutes` | DOUBLE | stima centrale dell'attesa a quell'ora, modello misto (arrivi casuali + quota sincronizzata sull'orario, vedi T12); NULL se non abbinata o senza servizio in quell'ora |
| `wait_minutes_low` | DOUBLE | limite inferiore: min(attesa per "qualsiasi linea" con le partenze di tutte le linee combinate, stima centrale); NULL come sopra |
| `wait_minutes_high` | DOUBLE | limite superiore: headway/2 della linea meno frequente; NULL come sopra |
| `wait_minutes_random` | DOUBLE | vecchia stima, headway/2 con arrivi casuali (mediana tra le linee), per confronto |
| `exposed_wait_minutes` | DOUBLE | `exposure_score × wait_minutes`; NULL se `wait_minutes` è NULL |
| `risk_level` | VARCHAR | della fermata (non dell'ora): `low`, `medium`, `high` |
| `exposure_decile` | INTEGER | della fermata: decile (1–10) di `exposure_score_hours` tra tutte le fermate, 10 = più esposte |
| `risk_level_stable` | BOOLEAN | della fermata: `true` se `risk_level` è lo stesso per ogni `shelter_exposure_factor` in {0; 0,25; 0,5; 0,75; 1; 1,2} (vedi T13) |

Esposizione e attesa si riferiscono allo stesso giorno, domenica 28/06/2026 (attesa dal feed GTFS ATM versione 417, valido dall'8/06 al 5/07/2026). La finestra 13–19 CEST corrisponde alle ore 12–18 in ora solare dei dati ARPA.

## `main.mart_trees_map` — vista alberi (T15)
Una riga per albero valido del censimento comunale (ds2484, estrazione 31/03/2025): `tree_id` VARCHAR, `genus` VARCHAR, `species` VARCHAR, `height_m` DOUBLE, `crown_diameter_m` DOUBLE, `lon`, `lat` DOUBLE, `shades_stop` BOOLEAN (la sua chioma fa ombra ad almeno una fermata in almeno un'ora 13–19). Esclusi gli alberi senza altezza o chioma o con valori non plausibili (soglie in docs §4).

In `mart_stop_heat_risk` e `mart_stop_heat_wait_hourly` (a livello fermata): `n_trees_20m` INTEGER (alberi entro 20 m), `tree_shade_hours` INTEGER (ore 13–19 in ombra di chioma).

## `main.int_stop_wait_time` — vista attesa
Una riga per (`gtfs_stop_id`, `hour`) con `stop_name`, `lat`, `lon`, `median_wait_minutes` (headway/2 casuale, invariata), `n_lines`, `wait_time_bucket` e in più `median_headway_minutes`, `wait_any_line_minutes`, `wait_least_frequent_minutes`, `wait_mixed_minutes` (stessa definizione di `wait_minutes`, `wait_minutes_low`, `wait_minutes_high` sopra). `wait_time_bucket` si calcola su `wait_mixed_minutes`.

## Codifica visiva concordata (vista principale)
- Una colonna 3D per fermata OSM, per l'ora selezionata o la media 13–19.
- Altezza = `wait_minutes` (stima centrale), tetto a 25 min; il tooltip mostra anche l'intervallo `wait_minutes_low`–`wait_minutes_high`.
- Colore = `exposure_score`: ombra / pensilina al sole / sole pieno.
- Fermate con `wait_minutes` NULL: punto grigio a terra, senza colonna.

## Vista alberi (T15)
- Alberi come punti a terra, raggio = metà `crown_diameter_m` in metri, colore per `height_m`; caricati solo quando si apre la vista.
- Fermate sovrapposte, evidenziate se `tree_shade_hours` > 0.
- Tooltip albero: genere e specie, altezza, chioma. Tooltip fermata: ore in ombra di chioma, alberi entro 20 m.
