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
python prepare_tree_data.py           # -> data/trees.json (build_map.py runs it too)
python render_building_backdrop.py    # -> data/buildings.png, data/buildings_deck.png
python build_map.py                   # -> dist/site/ (static site) + dist/milan_heat_map.html (single file)
```

`prepare_main_data.py` must run before `render_building_backdrop.py`: the
deck.gl backdrop (`data/buildings_deck.png`) is rendered over the exact
bounds in `data/main.json`. This is also the order `.claude/loop.json`'s
frontend build command uses.

`build_map.py` always writes both outputs from the same `template.html`:

- **Static site, `dist/site/`** — `index.html` (no inline data), `data/*.json`,
  `data/*.png` (backdrops), `vendor/deck.gl-9.4.0.min.js` and `og.png`. The
  page loads its data with `fetch` (relative paths), so it needs HTTP:
  locally `cd dist/site && python3 -m http.server 8000` then open
  <http://localhost:8000/>; publish it by serving `dist/site/` as-is (GitHub
  Pages: https://n-iv-a.github.io/transit-heat-exposure-dbt/). Opened from `file://` it
  shows a readable error pointing to the single-file version.
- **Single file, `dist/milan_heat_map.html`** — data, images and deck.gl all
  inlined; open it directly in a browser, offline, no server. Use this one
  to share the map or for offline use.

**Publishing:** `.github/workflows/pages.yml` rebuilds the map from the
versioned seeds and deploys `dist/site/` on every push to `main` (or by hand
from the Actions tab). One-time manual setup: the repo must be public (free
plan) and Settings → Pages → Build and deployment → Source must be set to
**GitHub Actions**.

Open Graph / Twitter card meta tags are in both pages. `og.png` (1200x627) is
versioned in this folder and copied into `dist/site/` by `build_map.py`; it is
made by `render_og_image.py` (Playwright + Chromium screenshot of the site
served locally), which is *not* part of the build so CI needs no browser. Re-run
it by hand when the page changes: `python3 build_map.py && python3
render_og_image.py`.

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
| `prepare_tree_data.py` | `mart_trees_map` → `data/trees.json` (columnar, quantized; run by `build_map.py`, loaded on demand by the Trees view) |
| `render_building_backdrop.py` | Building-height raster → `data/buildings.png`, projected to match `template.html`'s own map projection |
| `build_map.py` | Fills the template's placeholders, writes `dist/site/` and `dist/milan_heat_map.html` |
| `render_og_image.py` | Manual: screenshots the site to `og.png` (versioned) |
| `og.png` | Social preview image, copied into `dist/site/` |
