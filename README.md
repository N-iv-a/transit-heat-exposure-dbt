# GTFS Valencia — dbt + DuckDB

Modellazione dimensionale (Kimball) di due feed di trasporto pubblico reali della Comunitat Valenciana — rete urbana e rete interurbana — con dbt e DuckDB. Nessun warehouse cloud: gira interamente su un file locale.

## 1. Problema

Un feed GTFS grezzo (file CSV con orari, fermate, linee) risponde male a domande operative del tipo *"quante corse passano da questa fermata, il sabato sera?"* — servono join multipli, gestione del calendario dei servizi e aggregazioni ripetute ogni volta. Questo progetto trasforma due feed GTFS eterogenei in uno star schema testato, pronto per rispondere a quel tipo di domande con una query.

## 2. Approccio

```
raw_emt.*, raw_gva.* (DuckDB, un CSV -> una tabella)
        │
        ▼
staging/emt/*, staging/gva/*   (pulizia, cast, chiavi prefissate per agenzia)
        │
        ▼
intermediate/
  int_service_dates      trip calendar -> date esatte di servizio
  int_service_days       date esatte -> "giorno tipo" (Monday, Saturday, ...)
  int_trips_enriched     trip + route + agency (grana: trip)
        │
        ▼
marts/
  dim_agency, dim_route, dim_stop, dim_date
  fct_trips            (grana: trip x data di servizio)
  fct_stop_times        (grana: trip x fermata, orario schedulato)
  mart_service_frequency   <- il mart di valore
  mart_stop_coverage
```

Due fonti, un modello unico: EMT Valencia (rete urbana, un solo operatore) e GVA (rete interurbana, 50 concessionari) hanno schemi GTFS leggermente diversi — vengono normalizzati nello staging e uniti a partire dall'intermediate layer, con `agency_code` come discriminante esplicito ovunque.

## 3. Scelte e trade-off

- **dbt-duckdb invece di un warehouse cloud.** Il progetto deve girare da un README con `git clone` + due comandi, non da un account Databricks/Snowflake. DuckDB legge i CSV direttamente e il file `.duckdb` è tutto lo stato necessario.
- **Chiavi surrogate prefissate per agenzia** (`EMT-1017`, `GVA-5105040`, ...) invece di assumere che gli ID non collidano tra le due fonti. È un formato meno pulito nelle viste, ma elimina un'intera classe di bug silenziosi da join sbagliati.
- **`mart_service_frequency` aggrega per "giorno tipo", non per data esatta.** Il feed EMT ha un calendario di 6 settimane, il feed GVA ne ha uno di sole 2 (nessun `calendar.txt`, solo eccezioni). Espandere `fct_stop_times` per ogni data di servizio avrebbe prodotto decine di milioni di righe per un beneficio analitico marginale — la domanda reale ("il sabato mattina è coperto?") si risponde a livello di giorno-tipo. `fct_trips`, invece, resta a grana data esatta: è lì che serve, per contare occorrenze reali nel periodo coperto dal feed.
- **`arrival_hour` è calcolato con un modulo 24**, non con un cast a `TIME`: GTFS ammette orari oltre le 24:00 per le corse notturne (es. `25:30:00`), che un tipo `TIME` standard rifiuterebbe.
- **Niente `dbt_utils` o altri package esterni.** Con due soli test custom necessari, aggiungere una dipendenza esterna (e la sua risoluzione di rete) non era giustificato.

## 4. Anti-features

- **Nessuna geometria dei percorsi.** `shapes.txt` non viene caricato: nessun modello di questo progetto ne ha bisogno, e sono 45+ MB di dati che avrebbero solo appesantito l'ingestion.
- **Nessuna gestione degli aggiornamenti incrementali.** L'ingestion fa sempre `create or replace table`: per un progetto dimostrativo, con feed che cambiano ogni giorno, mergiare in incrementale sarebbe complessità senza un problema reale da risolvere.
- **Nessun orchestratore.** Due comandi Python/dbt in sequenza, eseguiti a mano. Aggiungere Airflow o simili per un progetto locale a due fonti sarebbe puro over-engineering.

## 5. Cosa farei diversamente

- Il confronto EMT/GVA sul "giorno tipo" non è del tutto equo: EMT lo deriva da un pattern settimanale dichiarato (`calendar.txt`), GVA da date effettivamente osservate in una finestra di due settimane. Con un feed GVA più lungo nel tempo (es. uno storico raccolto via cron) si potrebbe validare se il pattern osservato è davvero stabile settimana su settimana.
- I dati orari di GVA contengono alcuni valori anomali (`47:xx:00`, ~20 righe su 192k) che sono stati normalizzati col modulo ma non investigati alla fonte: in un contesto reale andrebbero segnalati al publisher del feed, non solo silenziati.
- Un test di unicità composita su `fct_trips` esiste già come test singolare ad-hoc; con `dbt_utils.unique_combination_of_columns` sarebbe stato più leggibile — omesso qui solo per non introdurre una dipendenza esterna per un singolo test.

## 6. Come farlo girare

Richiede Python 3.10+.

```bash
git clone https://github.com/N-iv-a/gtfs-valencia-dbt
cd gtfs-valencia-dbt

python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

**Dati.** I feed GTFS non sono versionati nel repo (dati di terze parti, decine di MB). Scaricali ed estraili in `data/raw/<agenzia>/*.txt`:

- EMT Valencia (rete urbana): [Google Transit — Plataforma VLCi](https://opendata.vlci.valencia.es/en/dataset/google-transit-lines-stops-bus-schedules) → estrai in `data/raw/emt/`
- GVA (rete interurbana): [Itinerarios y horarios — Generalitat Valenciana](https://dadesobertes.gva.es/es/dataset/tra-hyr-atmv-horaris-i-rutes) → estrai in `data/raw/gva/`

```bash
python ingestion/load_gtfs.py      # CSV -> DuckDB (schemi raw_emt / raw_gva)
dbt build --profiles-dir .         # staging -> intermediate -> marts, con tutti i test
```

Esplora il risultato:

```bash
python3 -c "
import duckdb
con = duckdb.connect('gtfs.duckdb')
print(con.execute('select * from main.mart_service_frequency order by trip_count desc limit 10').fetchall())
"
```

---

*Costruito con l'assistenza di IA (Claude); architettura, scelte di modellazione e trade-off sono miei.*
