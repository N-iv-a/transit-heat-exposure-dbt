# Transit Heat Exposure — GTFS + dbt, multiple cities

Real-world GTFS feeds, modeled with dbt + DuckDB into a tested star schema —
one dbt project, extended city by city. Each city keeps its own detailed
data-decisions log (source evaluation, what was ruled out, trade-offs);
this README is the map between them.

No cloud warehouse: everything runs from a local DuckDB file, built with
`git clone` + a handful of commands.

## Architecture (shared across cities)

```
raw_<source>.*                    (DuckDB, one CSV -> one table, via ingestion/load_<source>.py)
        │
        ▼
staging/<source>/*                 (cleanup, casts, consistent keys/ids)
        │
        ▼
intermediate/                      (enrichment, grain changes)
        │
        ▼
marts/                             (the tested, query-ready tables)
```

One dbt project, one `gtfs.duckdb` file. Adding a city means adding a
`raw_<city>` schema, a `staging/<city>/` folder, and its own
`docs/<CITY>_DATA_DECISIONS.md` — not a new repo or a parallel pipeline.

## Cities

### Valencia — two feeds, one schema

EMT Valencia (urban, single operator) and GVA (interurban, 50
concessionaires): two real feeds with different GTFS schemas, normalized
into one star schema with agency-prefixed keys (`EMT-1017`, `GVA-5105040`).
`mart_service_frequency`, `mart_stop_coverage`.

→ [`docs/VALENCIA_DATA_DECISIONS.md`](docs/VALENCIA_DATA_DECISIONS.md)

### Milan — sun exposure & wait time at the stop

A single clean feed (ATM), extended past what GTFS alone can answer: is a
given stop in the sun or in shade, at the hours Milan's documented hottest
summer (2026) actually gets hot? Building-shadow geometry computed from a
Copernicus height raster + `pysolar`, OSM `shelter` tags as a second
signal, an empirically-derived critical window (ARPA weather stations) —
plus a separate, evolutionary wait-time-per-stop signal (per-line median
headway, not a combined-schedule shortcut). `mart_stop_heat_risk`,
`int_stop_wait_time`, and a self-contained map tool
(`scripts/milan/map/` → `dist/milan_heat_map.html`).

→ [`docs/MILAN_DATA_DECISIONS.md`](docs/MILAN_DATA_DECISIONS.md)

## Running it

```bash
git clone https://github.com/N-iv-a/transit-heat-exposure-dbt
cd transit-heat-exposure-dbt

python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Each city needs its own raw data (GTFS feeds are third-party data, not
versioned) and has its own ingestion + build steps — see the city's own
doc, section "Running it" / §6:

- Valencia: [`docs/VALENCIA_DATA_DECISIONS.md`, §6](docs/VALENCIA_DATA_DECISIONS.md#6-running-it)
- Milan: needs a separate virtualenv (`scripts/milan/requirements.txt` —
  rasterio/pyproj/pysolar aren't needed for Valencia) — see
  [`docs/MILAN_DATA_DECISIONS.md`, §9](docs/MILAN_DATA_DECISIONS.md#9-running-it)
  and [`scripts/milan/map/README.md`](scripts/milan/map/README.md) for the
  map tool.

Both cities build into the same `gtfs.duckdb` file — `dbt build
--profiles-dir .` with no `--select` runs every city's models and tests
together.

---

*Built with AI assistance (Claude); architecture, modeling choices and
trade-offs are mine.*
