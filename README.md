# Milan Heat Exposure — transit stop sun exposure & wait time

Branch: `milan-heat-exposure`. An evolution of this repo's Valencia GTFS/dbt
project's original "Transit Heat Exposure" concept, moved to a real Milan
dataset — kept on its own branch so Valencia's `main` stays untouched and
green. Every data-sourcing decision below is logged in full, with what was
ruled out and why, in
[`docs/MILAN_DATA_DECISIONS.md`](docs/MILAN_DATA_DECISIONS.md).

## 1. Problem

On a hot summer day, "how long is my wait" isn't the only thing that
matters at a bus/tram/metro stop — whether you're standing in direct sun or
in shade does too. Milan's summer 2026 was, by ARPA Lombardia's own data,
its hottest since 1951. This project asks two separate, concrete questions
about that summer, per stop: *am I in the sun, and for how long do I have
to be?* — using real building-height, weather-station, and OSM data rather
than assumed defaults.

## 2. Approach

```
data_milan/raw/gtfs/*.txt (ATM Milano feed, not versioned)
data_milan/seeds/building_height/*.tif  (Copernicus Urban Atlas, EPSG:3035)
data_milan/seeds/osm_shelter/*.geojson  (OSM `shelter` tag via Overpass)
data_milan/seeds/weather/*.csv          (ARPA Lombardia, 6 city stations)
        │
        ▼  scripts/milan/solar_exposure.py   (shadow raster-march + shelter)
        ▼  scripts/milan/wait_time.py        (per-line-then-median headway/2)
        │
data_milan/seeds/stop_solar_exposure.csv   (OSM node id x hour)
data_milan/seeds/stop_wait_time.csv        (GTFS stop_id x hour)
        │
        ▼  ingestion/load_milan.py  ->  raw_milan.* (DuckDB)
        ▼
staging/milan/
  stg_stop_solar_exposure
        │
intermediate/
  int_stop_wait_time
        │
marts/
  mart_stop_heat_risk        <- stop-grain risk_level (low/medium/high)
        │
        ▼  scripts/milan/map/  (prepare_*.py, render_building_backdrop.py, build_map.py)
dist/milan_heat_map.html   <- self-contained, no server needed
```

Two independent signals, two independent pipelines, on purpose: exposure
(sun/shade) keys off OSM node ids, wait time keys off GTFS `stop_id`s, and
no join between the two ID spaces is attempted anywhere in this project —
see trade-offs below.

## 3. Choices and trade-offs

- **The critical window (June 28 2026, 12:00–18:00) is derived from real
  ARPA weather-station data, not assumed.** Six Milan stations' 10-minute
  readings, May–September 2026, were analyzed to find both the hottest day
  and the hours where >30°C readings peak (60%+ of readings, 13:00–17:00).
  A byproduct finding: averaging across all 6 stations shows Milan's
  "heat wave" as one continuous 69-day window, not the two separate waves
  press coverage (citing a likely single reference station) described —
  a real artifact of station choice, documented in
  `docs/MILAN_DATA_DECISIONS.md` §5 rather than smoothed over.
- **Building height from Copernicus Urban Atlas, not Regione Lombardia
  LiDAR.** The higher-accuracy LiDAR source is restricted to Lombard public
  administrations; Urban Atlas is open, same resolution class (10m) as the
  PNOA data used for Valencia, at the cost of a 2012 reference year (the
  skyline has changed since — declared, not hidden).
- **Shadow casting computed in-house** (raster ray-march via `pysolar` +
  the height raster), not via a third-party shadow service (ShadeMap was
  evaluated and ruled out — no clear redistribution license, and this
  project holds itself to "reproducible via `git clone` + documented
  setup," the same bar the Valencia repo sets). The script prints its own
  computed error margin per hour rather than asserting accuracy.
- **Wait time: per-line median, then median across lines — the more
  expensive method, chosen deliberately over a cheaper combined-schedule
  shortcut.** It answers "how long do I wait for *my* line," which is what
  a rider actually experiences, not "how long until any vehicle regardless
  of line."
- **Exposure and wait time are two separate marts, not one joined signal.**
  `stg_stop_solar_exposure` keys off OSM node ids (from the Overpass
  shelter export), `int_stop_wait_time` off GTFS `stop_id`s — two ID
  spaces with no shared key. Forcing a join would silently drop or
  duplicate rows; keeping them separate (two marts, two maps) is the
  honest representation of what the data actually supports today.
- **Reference days aren't always the same date the finding is about.**
  Shadow/shelter exposure uses June 28 2026 itself (the hottest day
  found). Wait time uses September 13 2026 instead — the ATM GTFS feed is
  a present-plus-near-future snapshot that simply doesn't retain June's
  schedule — matched by weekday (both Sundays) rather than by date.

## 4. Anti-features

- **No live basemap on the map tool.** Tile servers (OpenStreetMap and
  otherwise) aren't reachable from a published Claude artifact's CSP, nor
  from the sandbox this was built in. The map instead renders its own
  building-height raster as a backdrop, reprojected to match the map's own
  projection exactly — this project's own already-validated data standing
  in for a basemap, not a placeholder.
- **No attempt to reconcile OSM and GTFS stop ids.** A nearest-point match
  between the two ID spaces is a reasonable next step if the two signals
  are ever meant to be read as one, but it wasn't attempted here — see
  trade-offs above.
- **No multi-day exposure analysis.** June 28 is one representative day
  within a much longer hot window (June 13–August 20); computing every day
  in that range would multiply the shadow-march cost for marginal
  additional insight over "the single hottest day, done precisely."

## 5. What I'd do differently

- The map tool (`scripts/milan/map/`) was built iteratively as a
  dev/verification aid and still carries a dark-mode-first dashboard
  styling that doesn't fully suit the final deliverable. A plain,
  white-background version is the planned next pass — see "Known
  aesthetic issues" in `scripts/milan/map/README.md` for the specific,
  already-identified list.
- A nearest-point join between the OSM and GTFS stop id spaces, if pursued,
  would let a single combined map show both signals per physical stop
  instead of two separate maps.
- The shadow model is a single representative day; a version that
  aggregates across the full June 13–August 20 hot window would answer
  "how exposed is this stop across the whole hot season," a stronger claim
  than "on the single hottest day."

## 6. Running it

Requires Python 3.10+. Uses a separate virtualenv from the Valencia
project (`.venv-milan`) since the two have different dependencies
(rasterio, pyproj, pysolar are Milan-only).

```bash
git clone https://github.com/N-iv-a/gtfs-valencia-dbt
cd gtfs-valencia-dbt
git checkout milan-heat-exposure

python3 -m venv .venv-milan && source .venv-milan/bin/activate
pip install -r scripts/milan/requirements.txt
```

**Data.** Building height, OSM shelter, and ARPA weather CSVs are already
committed under `data_milan/seeds/` (open-license third-party data, small
enough to version). The GTFS feed itself is not — download and extract the
ATM Milano feed (`dati.comune.milano.it/gtfs.zip`) to `data_milan/raw/gtfs/`.

```bash
python scripts/milan/solar_exposure.py   # -> data_milan/seeds/stop_solar_exposure.csv
python scripts/milan/wait_time.py        # -> data_milan/seeds/stop_wait_time.csv

python ingestion/load_milan.py           # CSVs -> DuckDB (raw_milan schema)
dbt build --profiles-dir . --select stg_stop_solar_exposure int_stop_wait_time mart_stop_heat_risk
```

Explore the result:

```bash
python3 -c "
import duckdb
con = duckdb.connect('gtfs.duckdb')
print(con.execute('select risk_level, count(*) from main.mart_stop_heat_risk group by 1').fetchall())
"
```

**Map tool** (optional — separate deps, see `scripts/milan/map/README.md`
for the full pipeline and its known deferred aesthetic issues):

```bash
cd scripts/milan/map
python prepare_exposure_data.py && python prepare_wait_data.py \
  && python render_building_backdrop.py && python build_map.py
# -> dist/milan_heat_map.html, open directly in a browser
```

---

*Built with AI assistance (Claude); architecture, modeling choices and
trade-offs are mine.*
