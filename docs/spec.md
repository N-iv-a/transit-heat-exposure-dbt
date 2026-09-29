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
- Finestra oraria critica: **13:00–19:00 CEST**, ricavata dai dati ARPA (ore con più letture > 30 °C), non assunta. ARPA dichiara gli orari in ora solare (UTC+1): le sue ore 12–18 sono 13–19 CEST.
- Giorno dell'attesa: lo stesso 28 giugno 2026 (domenica), dal feed GTFS ATM versione 417 (valido 8/06–5/07/2026): esposizione e attesa si riferiscono allo stesso giorno.

**Spazio e dati**
- Altezza edifici: Copernicus Urban Atlas **2012**, raster 10 m. Gli edifici costruiti dopo il 2012 (Porta Nuova, CityLife) mancano.
- Pensiline: tag OSM `shelter` sulle 2.931 fermate bus/tram (96,7% taggate), trattato come affidabile.
- Alberi: censimento alberi del Comune di Milano (ds2484, 31/03/2025; licenza da verificare), 248.073 alberi validi su 251.165 (altezza 1–45 m, chioma 0,5–30 m). Chioma = cilindro verticale (da 1/3 dell'altezza alla cima); ombra di chioma se il raggio verso il sole lo attraversa; trasmissività 3% (`tree_transmissivity`, Konarska et al. 2014). Solo alberi comunali, nessun albero privato. Dettagli in `docs/MILAN_DATA_DECISIONS.md` §3.1.
- Fermate OSM (esposizione) e GTFS (attesa) sono due insiemi di ID diversi, collegati per tag `ref` o per prossimità (vedi Regole).

**Comportamento del passeggero**
- Arrivo casuale alla fermata: attesa attesa = metà dell'intervallo tra due passaggi (headway/2).
- Il passeggero aspetta **la sua linea**, non un mezzo qualsiasi.

## Regole teoriche applicate
1. **Posizione del sole** (pysolar): azimut ed elevazione per fermata e ora, ora legale CEST.
2. **Ombra degli edifici** (ray marching sul raster): dalla fermata verso il sole a passi di 10 m; la fermata è in ombra se a distanza *d* c'è un edificio più alto di *d · tan(elevazione)*. Il raggio di ricerca è calcolato per ora come altezza massima del raster (125 m) / tan(elevazione), da 60 m (13–14) a 330 m (19:00): nessun edificio del raster può fare ombra oltre il raggio.
3. **Punteggio di esposizione orario**: ombra di edificio **0**; sole con pensilina **0,5** (`shelter_exposure_factor`: la pensilina attenua ma non rinfresca come un'ombra vera); sole senza pensilina **1**. La lettura binaria originale (esposta = né ombra né pensilina) resta nelle colonne `_binary`.
4. **Rischio calore per fermata**: somma dei punteggi sulle 7 ore (0–7); alto ≥ 5, basso ≤ 1, medio altrimenti.
5. **Attesa per fermata e ora**: per linea, mediana degli intervalli tra partenze nell'ora, divisa per 2; poi mediana tra le linee della fermata; gli intervalli > 3 h (ultime corse) sono esclusi.
6. **Collegamento OSM ↔ GTFS**: prima `ref` OSM = `stop_id` GTFS (entro 200 m, controllo di coerenza), poi fermata GTFS più vicina entro 30 m (distanza haversine), altrimenti non abbinata.
7. **Attesa al sole**: per ogni ora punteggio × attesa di quella stessa ora; media sulle ore con servizio = `avg_exposed_wait_minutes`, cioè i minuti medi che un passeggero passa ad aspettare sotto il sole. L'attesa è il modello misto (arrivi casuali + quota sincronizzata sull'orario, con limiti inferiore e superiore): `docs/MILAN_DATA_DECISIONS.md` §7.1. Stessa definizione in dbt e nella mappa.
8. **Valencia**: chiavi con prefisso agenzia (`EMT-…`, `GVA-…`); orari oltre le 24:00 gestiti col modulo 24; frequenze aggregate per tipo di giorno, corse per data esatta.

## Output
**Tabelle dbt** (DuckDB `gtfs.duckdb`)
- Valencia: `dim_agency`, `dim_route`, `dim_stop`, `dim_date`, `fct_trips`, `fct_stop_times`, `mart_service_frequency`, `mart_stop_coverage`.
- Milano: `mart_stop_heat_risk` (rischio calore per fermata), `int_stop_wait_time` (attesa per fermata e ora), `int_osm_gtfs_stop_bridge` (collegamento degli ID), `mart_stop_heat_wait` (calore × attesa per fermata), `mart_stop_heat_risk_sensitivity` (classe di rischio per fattore pensilina), `mart_heat_wait_sensitivity` (attesa per `sync_share_max` e classe), `mart_trees_map` (alberi validi per la mappa; `n_trees_20m` e `tree_shade_hours` per fermata). Metrica: minuti di attesa al sole diretto, non stress termico.

**Risultati principali (Milano)**
- 854 fermate su 2.931 ad alto rischio calore (941 prima degli alberi; 442 con la lettura binaria), 246 a basso rischio. 656 fermate hanno almeno un'ora in ombra di chioma.
- Attesa al sole mediana (modello misto, con alberi): 5,2 min per le fermate ad alto rischio (p90 6,6), 2,3 per il medio, 0,4 per il basso. Coppie fermata-ora esposte: 32,6% (34,9% senza alberi).
- 2.627 fermate collegate al GTFS (2.511 per `ref`, 116 per prossimità), 304 senza abbinamento.

**Mappa**: `scripts/milan/map/dist/milan_heat_map.html`, pagina HTML autocontenuta (~6 MB: dati, sfondo edifici e deck.gl incorporati). Vista principale 3D **Calore × attesa**: una colonna per fermata, altezza = attesa (tetto 25 min), colore = punteggio di esposizione, ora per ora o media 13–19; sotto-viste Esposizione e Attesa. Legge da dbt (`contract/map_data.md`).

**Test**: data test dbt (unicità, valori ammessi, soglie di distanza, punteggio valido, quota di fermate `unmatched` ≤ 12%, `exposure_score_hours` tra 0 e 7, 7 righe orarie per fermata, `risk_level` coerente con il punteggio, 6 righe per fermata nella sensitività pensilina, decili 1–10, 12 righe nella sensitività attesa coerenti col mart principale) e 12 test pytest sul calcolo dell'ombra.

## Fuori scope (per ora)
Più giorni oltre il 28 giugno; alberi privati e stagionalità delle chiome; seconda rete milanese (Trenord); mappa stradale di sfondo; aggiornamenti incrementali e orchestratore.

## Architettura
`raw_<fonte>.*` (ingestion) → `staging/<fonte>/` → `intermediate/` → `marts/`. Un solo progetto dbt, un solo `gtfs.duckdb`. Aggiungere una città = schema `raw_<città>`, cartella `staging/<città>/`, doc `docs/<CITTÀ>_DATA_DECISIONS.md`.

Log delle decisioni: `README.md` (mappa generale), `docs/VALENCIA_DATA_DECISIONS.md`, `docs/MILAN_DATA_DECISIONS.md`.

## Contratto
Formato dei dati tra dbt e mappa: `contract/map_data.md`. La mappa legge da `gtfs.duckdb` (`mart_stop_heat_wait_hourly`, `int_stop_wait_time`) dopo il build dbt di Milano; cambiarne le colonne è una modifica di contratto.
Fermate OSM (esposizione) e GTFS (attesa) sono collegate in dbt da `int_osm_gtfs_stop_bridge` (prima `ref` OSM, poi fermata più vicina entro 30 m); vista combinata in `mart_stop_heat_wait` (per fermata) e `mart_stop_heat_wait_hourly` (per fermata e ora).
