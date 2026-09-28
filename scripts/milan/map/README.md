# Milan heat exposure — map visualization tool

Development/verification tool: watches the pipeline's output (solar
exposure, wait time) as a map instead of just numbers in a terminal. Not
the final presentation — see "Known aesthetic issues" below for what's
explicitly deferred to a later polish pass. Styling is now a plain,
white-background page (system fonts, flat surfaces, a single light theme).

The `prepare_*` scripts read from `gtfs.duckdb` at the project root (tables
`main.mart_stop_heat_wait_hourly` and `main.int_stop_wait_time`, per
`contract/map_data.md`) — not from CSVs. That means `gtfs.duckdb` needs the
Milan dbt models built first (`python3 ingestion/load_milan.py && dbt run
--profiles-dir . --select source:raw_milan+` from the project root).

## Running it

```bash
pip install -r ../requirements.txt

# from the project root, once, so gtfs.duckdb has the Milan marts:
python3 ../../../ingestion/load_milan.py
cd ../../.. && dbt run --profiles-dir . --select source:raw_milan+ && cd scripts/milan/map

python prepare_main_data.py           # -> data/main.json (main deck.gl view)
python prepare_exposure_data.py       # -> data/exposure.json
python prepare_wait_data.py           # -> data/wait_time.json
python render_building_backdrop.py    # -> data/buildings.png, data/buildings_deck.png
python build_map.py                   # -> dist/milan_heat_map.html
```

`prepare_main_data.py` must run before `render_building_backdrop.py`: the
deck.gl backdrop (`data/buildings_deck.png`) is rendered over the exact
bounds in `data/main.json`. This is also the order `.claude/loop.json`'s
frontend build command uses.

Open `dist/milan_heat_map.html` directly in a browser — everything (data,
the backdrop images, the vendored `vendor/deck.gl-9.4.0.min.js` bundle) is
inlined, no server needed and no network requests made.

`data/` and `dist/` are gitignored: both are generated from `gtfs.duckdb`
(itself built from the seeds in `data_milan/seeds/`), not source.

## Known aesthetic issues (deferred — noted, not forgotten)

- **No live street/photo basemap.** Tile servers aren't reachable from a
  published Claude artifact or from the sandbox this was built in (see
  `docs/MILAN_DATA_DECISIONS.md`, §4). Current backdrop is the project's own
  building-height raster instead. A road-vector alternative (OSM ways via
  Overpass, drawn as thin lines) was offered and not yet pursued — export
  attempt via chat upload didn't come through as a usable file.
- **Wait-time map has no backdrop at all.** Different, larger bounding box
  than the exposure map's OSM stops (GTFS stops extend further out) — the
  backdrop would need regenerating at that extent, not reused as-is.

## Files

| File | Role |
|---|---|
| `template.html` | The page itself — versioned source of truth. Has `__PLACEHOLDER__` markers where data gets injected. |
| `prepare_exposure_data.py` | `stop_solar_exposure.csv` + OSM shelter geojson → `data/exposure.json` |
| `prepare_wait_data.py` | `stop_wait_time.csv` → `data/wait_time.json` |
| `render_building_backdrop.py` | Building-height raster → `data/buildings.png`, projected to match `template.html`'s own map projection |
| `build_map.py` | Fills the template's placeholders, writes `dist/milan_heat_map.html` |
