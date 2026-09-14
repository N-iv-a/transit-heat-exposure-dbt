# Valencia — Data Decisions Log

The first project in this repo, kept here for reference alongside
[`docs/MILAN_DATA_DECISIONS.md`](MILAN_DATA_DECISIONS.md). Dimensional
modeling (Kimball) of two real public transit feeds from the Comunitat
Valenciana — urban and interurban networks — built with dbt and DuckDB, no
cloud warehouse.

## 1. Problem

A raw GTFS feed (CSV files with schedules, stops, routes) answers
operational questions like *"how many trips pass this stop on Saturday
evening?"* badly — it takes multiple joins, service-calendar handling, and
the same aggregations rebuilt every time. This project turns two
heterogeneous GTFS feeds into a tested star schema, ready to answer that
kind of question with a single query.

## 2. Approach

```
raw_emt.*, raw_gva.* (DuckDB, one CSV -> one table)
        │
        ▼
staging/emt/*, staging/gva/*   (cleanup, casts, agency-prefixed keys)
        │
        ▼
intermediate/
  int_service_dates      trip calendar -> exact service dates
  int_service_days       exact dates -> "day type" (Monday, Saturday, ...)
  int_trips_enriched     trip + route + agency (grain: trip)
        │
        ▼
marts/
  dim_agency, dim_route, dim_stop, dim_date
  fct_trips            (grain: trip x service date)
  fct_stop_times        (grain: trip x stop, scheduled time)
  mart_service_frequency   <- the value mart
  mart_stop_coverage
```

Two sources, one model: EMT Valencia (urban network, single operator) and
GVA (interurban network, 50 concessionaires) have slightly different GTFS
schemas — normalized in staging and merged from the intermediate layer
onward, with `agency_code` as an explicit discriminant everywhere.

## 3. Choices and trade-offs

- **dbt-duckdb instead of a cloud warehouse.** The project needs to run
  from a README with `git clone` + two commands, not from a
  Databricks/Snowflake account. DuckDB reads the CSVs directly and the
  `.duckdb` file is all the state that's needed.
- **Agency-prefixed surrogate keys** (`EMT-1017`, `GVA-5105040`, ...)
  instead of assuming IDs don't collide between the two sources. It's a
  less clean-looking format in the views, but it eliminates an entire
  class of silent bad-join bugs.
- **`mart_service_frequency` aggregates by "day type", not by exact
  date.** The EMT feed has a 6-week calendar, the GVA feed only 2 (no
  `calendar.txt`, exceptions only). Expanding `fct_stop_times` by every
  service date would have produced tens of millions of rows for marginal
  analytical benefit — the real question ("is Saturday morning covered?")
  is answered at the day-type level. `fct_trips`, on the other hand, stays
  at exact-date grain: that's where it's needed, to count real occurrences
  within the feed's coverage window.
- **`arrival_hour` is computed with a modulo 24**, not a cast to `TIME`:
  GTFS allows times past 24:00 for overnight trips (e.g. `25:30:00`),
  which a standard `TIME` type would reject.
- **No `dbt_utils` or other external packages.** With only two custom
  tests needed, pulling in an external dependency (and its network
  resolution) wasn't justified.

## 4. Anti-features

- **No route shape geometry.** `shapes.txt` is never loaded: no model in
  this project needs it, and it's 45+ MB of data that would only have
  slowed down ingestion.
- **No incremental-update handling.** Ingestion always does `create or
  replace table`: for a demo project with daily-changing feeds, building
  incremental merge logic would be complexity without a real problem to
  solve.
- **No orchestrator.** Two Python/dbt commands run by hand, in sequence.
  Adding Airflow or similar for a local, two-source project would be pure
  over-engineering.

## 5. What I'd do differently

- The EMT/GVA "day type" comparison isn't entirely fair: EMT derives it
  from a declared weekly pattern (`calendar.txt`), GVA from dates actually
  observed in a two-week window. With a longer-running GVA feed (e.g. a
  history collected via cron) it would be possible to validate whether the
  observed pattern is actually stable week over week.
- GVA's time data contains a handful of anomalous values (`47:xx:00`, ~20
  rows out of 192k) that were normalized with the modulo but never
  investigated at the source: in a real setting these should be reported
  to the feed publisher, not just silently handled.
- A composite-uniqueness test on `fct_trips` already exists as an ad-hoc
  singular test; `dbt_utils.unique_combination_of_columns` would have read
  more cleanly — left out only to avoid an external dependency for a
  single test.

## 6. Running it

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

**Data.** The GTFS feeds aren't versioned in the repo (third-party data,
tens of MB). Download and extract them into `data/raw/<agency>/*.txt`:

- EMT Valencia (urban network): [Google Transit — Plataforma VLCi](https://opendata.vlci.valencia.es/en/dataset/google-transit-lines-stops-bus-schedules) → extract to `data/raw/emt/`
- GVA (interurban network): [Itinerarios y horarios — Generalitat Valenciana](https://dadesobertes.gva.es/es/dataset/tra-hyr-atmv-horaris-i-rutes) → extract to `data/raw/gva/`

```bash
python ingestion/load_gtfs.py      # CSV -> DuckDB (raw_emt / raw_gva schemas)
dbt build --profiles-dir . --select staging.emt staging.gva intermediate marts.dim_agency marts.dim_route marts.dim_stop marts.dim_date marts.fct_trips marts.fct_stop_times marts.mart_service_frequency marts.mart_stop_coverage
```

Explore the result:

```bash
python3 -c "
import duckdb
con = duckdb.connect('gtfs.duckdb')
print(con.execute('select * from main.mart_service_frequency order by trip_count desc limit 10').fetchall())
"
```
