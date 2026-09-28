# Transit Heat Exposure: fonte di verità

Obiettivo, assunzioni, regole, output, architettura, contratto. Gli agent la leggono quando pianificano; tienila corta e aggiornata. Il dettaglio di ogni decisione (fonti scartate, numeri, verifiche) sta nei log per città.

## Scopo
Misurare **quanto a lungo un passeggero aspetta il mezzo pubblico sotto il sole**, fermata per fermata e ora per ora, nelle ore più calde dell'estate. Il risultato serve a indicare dove una pensilina, un albero o una frequenza più alta ridurrebbero di più il disagio da caldo.

Due livelli, un solo progetto dbt + DuckDB:
- **Valencia** (base): due feed GTFS eterogenei (EMT urbano, GVA interurbano) normalizzati in uno star schema testato che risponde a domande di servizio («quante corse passano da questa fermata il sabato sera?»).
- **Milano** (estensione): oltre il GTFS, esposizione solare alla fermata (ombra degli edifici + pensilina), tempo di attesa per fermata e loro combinazione.

Tutto riproducibile con `git clone` e pochi comandi: nessun cloud warehouse, nessun servizio a pagamento, solo open data.

## Assunzioni
Ogni assunzione è dichiarata, non nascosta; i limiti sono parte del risultato.

**Tempo**
- Giorno di studio dell'esposizione: **28 giugno 2026**, il più caldo dell'estate 2026 a Milano (media cittadina delle massime 38,2 °C, 6 stazioni ARPA). Un solo giorno rappresentativo, non l'intera ondata 13/06–20/08.
- Finestra oraria critica: **12:00–18:00**, ricavata dai dati ARPA (ore con più letture > 30 °C), non assunta.
- Giorno di riferimento dell'attesa: **13 settembre 2026**, domenica come il 28 giugno, perché il feed ATM non copre giugno. Esposizione e attesa si riferiscono quindi a due giorni diversi dello stesso tipo: approssimazione v1 dichiarata.

**Spazio e dati**
- Altezza edifici: Copernicus Urban Atlas **2012**, raster 10 m. Gli edifici costruiti dopo il 2012 (Porta Nuova, CityLife) mancano.
- Pensiline: tag OSM `shelter` sulle 2.931 fermate bus/tram (96,7% taggate), trattato come affidabile.
- Alberi: **non modellati**. La copertura OSM degli alberi stradali è troppo irregolare; oggi l'ombra viene solo da edifici e pensiline.
- Fermate OSM (esposizione) e GTFS (attesa) sono due insiemi di ID diversi, collegati per tag `ref` o per prossimità (vedi Regole).

**Comportamento del passeggero**
- Arrivo casuale alla fermata: attesa attesa = metà dell'intervallo tra due passaggi (headway/2).
- Il passeggero aspetta **la sua linea**, non un mezzo qualsiasi.

## Regole teoriche applicate
1. **Posizione del sole** (pysolar): azimut ed elevazione per fermata e ora, ora legale CEST.
2. **Ombra degli edifici** (ray marching sul raster): dalla fermata verso il sole a passi di 10 m fino a 80 m; la fermata è in ombra se a distanza *d* c'è un edificio più alto di *d · tan(elevazione)*. Errore dichiarato: oltre 80 m sfuggono edifici > 71 m alle 17:00 e > 49 m alle 18:00; nessuno alle 12–16 (l'edificio più alto misura 125 m).
3. **Punteggio di esposizione orario**: ombra di edificio **0**; sole con pensilina **0,5** (`shelter_exposure_factor`: la pensilina attenua ma non rinfresca come un'ombra vera); sole senza pensilina **1**. La lettura binaria originale (esposta = né ombra né pensilina) resta nelle colonne `_binary`.
4. **Rischio calore per fermata**: somma dei punteggi sulle 7 ore (0–7); alto ≥ 5, basso ≤ 1, medio altrimenti.
5. **Attesa per fermata e ora**: per linea, mediana degli intervalli tra partenze nell'ora, divisa per 2; poi mediana tra le linee della fermata; gli intervalli > 3 h (ultime corse) sono esclusi.
6. **Collegamento OSM ↔ GTFS**: prima `ref` OSM = `stop_id` GTFS (entro 200 m, controllo di coerenza), poi fermata GTFS più vicina entro 30 m (distanza haversine), altrimenti non abbinata.
7. **Attesa al sole**: per ogni ora punteggio × attesa mediana; media sulle 7 ore = `avg_exposed_wait_minutes`, cioè i minuti medi che un passeggero passa ad aspettare sotto il sole.
8. **Valencia**: chiavi con prefisso agenzia (`EMT-…`, `GVA-…`); orari oltre le 24:00 gestiti col modulo 24; frequenze aggregate per tipo di giorno, corse per data esatta.

## Output
**Tabelle dbt** (DuckDB `gtfs.duckdb`)
- Valencia: `dim_agency`, `dim_route`, `dim_stop`, `dim_date`, `fct_trips`, `fct_stop_times`, `mart_service_frequency`, `mart_stop_coverage`.
- Milano: `mart_stop_heat_risk` (rischio calore per fermata), `int_stop_wait_time` (attesa per fermata e ora), `int_osm_gtfs_stop_bridge` (collegamento degli ID), `mart_stop_heat_wait` (calore × attesa per fermata).

**Risultati principali (Milano)**
- 1.056 fermate su 2.931 ad alto rischio calore (724 con la lettura binaria), 91 a basso rischio.
- Attesa al sole mediana: 8,6 min per le fermate ad alto rischio (p90 11,4), 1,1 min per quelle a basso rischio.
- 2.591 fermate collegate al GTFS (2.466 per `ref`, 125 per prossimità), 340 senza abbinamento.

**Mappa**: `scripts/milan/map/dist/milan_heat_map.html`, pagina HTML autocontenuta (dati e sfondo edifici incorporati) con le viste esposizione e attesa.

**Test**: data test dbt (unicità, valori ammessi, soglie di distanza, punteggio valido) e 7 test pytest sul calcolo dell'ombra.

## Fuori scope (per ora)
Più giorni oltre il 28 giugno; alberi; seconda rete milanese (Trenord); mappa stradale di sfondo; aggiornamenti incrementali e orchestratore.

## Architettura
`raw_<fonte>.*` (ingestion) → `staging/<fonte>/` → `intermediate/` → `marts/`. Un solo progetto dbt, un solo `gtfs.duckdb`. Aggiungere una città = schema `raw_<città>`, cartella `staging/<città>/`, doc `docs/<CITTÀ>_DATA_DECISIONS.md`.

Log delle decisioni: `README.md` (mappa generale), `docs/VALENCIA_DATA_DECISIONS.md`, `docs/MILAN_DATA_DECISIONS.md`.

## Contratto
Nessun contratto formale in `contract/`. La mappa (`scripts/milan/map/`) legge i seed `data_milan/seeds/stop_solar_exposure.csv`, `stop_wait_time.csv` e l'export OSM: cambiarne le colonne è una modifica di contratto.
Fermate OSM (esposizione) e GTFS (attesa) sono collegate in dbt da `int_osm_gtfs_stop_bridge` (prima `ref` OSM, poi fermata più vicina entro 30 m); vista combinata in `mart_stop_heat_wait`.
