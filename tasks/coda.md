# Coda

Formato: `- [ ] ID [BE|FE|MIX] [S|M|L] titolo — dettagli {override opzionali}`
Override: gli stessi controlli di loop.json, per esempio `{gate=full test=agent}` o `{model.dev=opus}`.
BE = dbt/ingestion/script Milano, FE = tool mappa.

- [x] T01 [BE] [M] Ponte fermate OSM↔GTFS e mart calore × attesa (Milano) — caricare le fermate OSM di `data_milan/seeds/osm_shelter/export_shelter_milano.geojson` in `raw_milan` (id nodo, ref, nome, lon, lat) da `ingestion/load_milan.py`; modello di ponte `osm_node_id → gtfs_stop_id` con `match_method`: prima `ref` OSM = `stop_id` GTFS (distanza ≤ 200 m come controllo di coerenza), poi fermata GTFS più vicina entro 30 m, altrimenti non abbinata; `distance_m` calcolata con haversine in SQL. Analisi preliminare: 2.466/2.931 abbinate per ref (mediana 8,6 m), il più vicino da solo concorda col ref solo nel 92% dei casi. Nuovo mart per fermata OSM: campi di `mart_stop_heat_risk` + `gtfs_stop_id`, `match_method`, attesa mediana nella finestra 12–18, e `avg_exposed_wait_minutes` = media sulle 7 ore di (esposta ? attesa mediana : 0), cioè minuti medi di attesa sotto il sole. Test dbt: unicità osm_node_id, accepted_values su match_method, distanza entro soglia per metodo. Aggiornare i commenti che dicono «nessun join tra i due spazi di ID». Dichiarare nei commenti che esposizione (28/06) e attesa (13/09) hanno giorni di riferimento diversi.
- [ ] T02 [FE] [L] Versione finale della mappa: pagina a sfondo bianco — secondo `scripts/milan/map/README.md`: sostituire lo stile da dashboard scuro/crema con una pagina bianca e sobria; togliere modalità scura e toggle tema; nessuna risorsa esterna (via Google Fonts, font di sistema); stesse due viste (esposizione, attesa) e stessi dati, nessun cambio a script di preparazione o seed; leggibile su mobile. Aggiornare la sezione del README della mappa sui problemi estetici rinviati.

## In attesa (non eseguire)
- Copertura oltre il solo 28 giugno (finestra 13/06–20/08): rilevanza bassa per ora.
- Strade OSM come sfondo, sfondo edifici per la mappa attesa, segnalazione anomalie GVA, feed GVA storico, allineamento nome repo nel README.
