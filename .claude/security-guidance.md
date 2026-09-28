# Regole di sicurezza

Letto dal security-reviewer. Le regole generali valgono per ogni progetto; le specifiche si aggiungono in fondo.

## Generali
- Nessun dato personale vero in codice, test, seed, docs, commit o contract/. Solo dati fittizi, domini example.*.
- Nessuna chiave o token nel codice o nell'output di build: si inseriscono a runtime o stanno in .env, che è ignorato.
- Nei test ogni servizio esterno è simulato.
- Verso servizi esterni escono solo i campi necessari.
- Se il progetto usa un modello linguistico, il suo output è input non fidato: validato con uno schema prima di cambiare lo stato, reso come testo.
- Ogni nuova dipendenza è giustificata nel report.
- Esportazioni di dati personali sempre cifrate.
- Frontend: nessuno script da CDN, nessun analytics non dichiarato; se c'è una CSP, connessioni solo verso i domini previsti.

## Specifiche del progetto
- Solo open data di terze parti (GTFS, Copernicus, OSM, ARPA): ogni nuova fonte va citata con licenza nel `docs/*_DATA_DECISIONS.md` della città.
- I feed GTFS grezzi (`data/raw/`, `data_milan/raw/`) e `gtfs.duckdb` non si versionano.
- Nei seed e negli export OSM niente campi di contatto (email, telefono) oltre quelli strettamente necessari all'analisi.
- La mappa è un HTML autocontenuto: nessuna tile, script o font da server esterni (font di sistema).
