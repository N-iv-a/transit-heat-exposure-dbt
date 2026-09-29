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

python prepare_main_data.py           # -> data/main.json (all OSM-stop views: exposure, wait, departures, bounds)
python prepare_exposure_data.py       # -> data/exposure.json (ids of sheltered stops)
python prepare_wait_data.py           # -> data/wait_time.json (GTFS stops, Wait view)
python prepare_tree_data.py           # -> data/trees.json (build_map.py runs it too)
python render_building_backdrop.py    # -> data/buildings_deck.png (backdrop)
python render_shadow_layers.py        # -> data/shadow_13.png .. shadow_19.png (build_map.py runs it too)
python build_map.py                   # -> dist/site/ (static site) + dist/milan_heat_map.html (single file)
```

`prepare_main_data.py` must run before `render_building_backdrop.py` and
`render_shadow_layers.py`: backdrop and shadow images are rendered over the exact
bounds in `data/main.json`, so they line up with each other and with the stops. This is also the order `.claude/loop.json`'s
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

## The page (T17, see `contract/map_data.md`)

One deck.gl map shared by four views (same map, controls and layout; only the
layers and the legend change): **Sun x wait** (start view), **Exposure**,
**Wait**, **Trees**. Hour selector (13:00-19:00 + average; hidden in Trees) and a
**Heatmap** toggle (HeatmapLayer weighted by the view's metric) are common.

- Sun x wait: dot colour = `exposed_wait_minutes` in 5 quantile classes (YlOrRd,
  breaks computed in the page from all stop-hours, real minutes in the legend),
  radius = `n_departures` (square root, 2.5-9 px). Hollow grey circle = OSM stop
  not linked to a GTFS stop; small grey dot = linked but no service that hour.
  Top-20 priority list under the map (clickable: centres and highlights the stop).
- Exposure: colour = `exposure_score` (hour) or its mean (average; tooltip shows the 0-7 sum).
- Building shadow for the selected hour (Sun x wait and Exposure): 7 PNGs made by
  `render_shadow_layers.py` (same algorithm as `solar_exposure.py`, vectorized;
  imports its sun position and search-radius functions). Average = the 7 overlaid.
- Sun compass only in Sun x wait and Exposure. Dashed ring = `risk_level_stable` false.
- Tooltip: stop details plus a strip with the 7 hours (score and wait minutes).
- Colour scales are sequential and colour-blind safe (no red/green pair).

Sizes (measured): site ~7.4 MB (trees.json 3.2 MB, shadow PNGs ~0.45 MB together);
single file ~9.4 MB, shadows included. `build_map.py` drops the shadows from the
single file only if it would exceed 13 MB.

## Tests

- `python3 -m pytest -q scripts/milan/map`: the vectorized shadow mask against
  the scalar reference in `solar_exposure.py`.
- `node smoke_test.mjs [screenshot_dir]` (needs node Playwright, e.g.
  `NODE_PATH=/opt/node22/lib/node_modules PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers`):
  opens site and single file at 1200 and 375 px and checks console errors, views,
  Heatmap toggle, compass, shadow per hour, tooltip strip, priority list.
- og.png was regenerated with the same Playwright (screenshot of the site at
  1200x627); `render_og_image.py` does the same with python Playwright.

## Known aesthetic issues (deferred)

- **No live street/photo basemap.** Tile servers aren't reachable from a
  published Claude artifact or from the sandbox (see `docs/MILAN_DATA_DECISIONS.md`,
  section 4); the backdrop is the project's own building-height raster.

## Files

| File | Role |
|---|---|
| `template.html` | The page itself — versioned source of truth. Has `__PLACEHOLDER__` markers where data gets injected. |
| `prepare_main_data.py` | `mart_stop_heat_wait_hourly` -> `data/main.json` (all views on OSM stops) |
| `prepare_exposure_data.py` | sheltered stop ids -> `data/exposure.json` (tooltip only) |
| `prepare_wait_data.py` | `int_stop_wait_time` -> `data/wait_time.json` |
| `prepare_tree_data.py` | `mart_trees_map` -> `data/trees.json` (columnar, quantized; loaded on demand by the Trees view) |
| `render_building_backdrop.py` | Building-height raster -> `data/buildings_deck.png` |
| `render_shadow_layers.py` | Raster + sun position -> `data/shadow_13..19.png` (transparent, same bounds as the backdrop) |
| `test_render_shadow_layers.py`, `smoke_test.mjs` | pytest for the shadow mask; browser smoke test |
| `build_map.py` | Fills the template's placeholders, writes `dist/site/` and `dist/milan_heat_map.html` |
| `render_og_image.py` | Manual: screenshots the site to `og.png` (versioned) |
| `og.png` | Social preview image, copied into `dist/site/` |
