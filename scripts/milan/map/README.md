# Milan heat exposure — map visualization tool

Development/verification tool: watches the pipeline's output (solar
exposure, wait time) as a map instead of just numbers in a terminal. Not
the final presentation — see "Known aesthetic issues" below for what's
explicitly deferred to a later polish pass (planned: a plain white-background
web page, not this dark-capable dashboard styling).

## Running it

```bash
pip install -r ../requirements.txt

python prepare_exposure_data.py       # -> data/exposure.json
python prepare_wait_data.py           # -> data/wait_time.json
python render_building_backdrop.py    # -> data/buildings_{light,dark}.png
python build_map.py                   # -> dist/milan_heat_map.html
```

Open `dist/milan_heat_map.html` directly in a browser — everything (data,
both backdrop images) is inlined, no server needed.

`data/` and `dist/` are gitignored: both are generated from the seeds in
`data_milan/seeds/`, not source.

## Known aesthetic issues (deferred — noted, not forgotten)

- **Building backdrop is too faint in dark mode.** Visible but low-contrast;
  needs a real contrast pass, not just nudging two hex values again.
- **No live street/photo basemap.** Tile servers aren't reachable from a
  published Claude artifact or from the sandbox this was built in (see
  `docs/MILAN_DATA_DECISIONS.md`, §4). Current backdrop is the project's own
  building-height raster instead. A road-vector alternative (OSM ways via
  Overpass, drawn as thin lines) was offered and not yet pursued — export
  attempt via chat upload didn't come through as a usable file.
- **Wait-time map has no backdrop at all.** Different, larger bounding box
  than the exposure map's OSM stops (GTFS stops extend further out) — the
  backdrop would need regenerating at that extent, not reused as-is.
- **General visual pass pending.** Palette, type, layout here were built for
  a working/dev tool, not the final deliverable. The plan is a simpler,
  white-background version once the underlying data/features are settled —
  don't polish this styling further until that decision is made.

## Files

| File | Role |
|---|---|
| `template.html` | The page itself — versioned source of truth. Has `__PLACEHOLDER__` markers where data gets injected. |
| `prepare_exposure_data.py` | `stop_solar_exposure.csv` + OSM shelter geojson → `data/exposure.json` |
| `prepare_wait_data.py` | `stop_wait_time.csv` → `data/wait_time.json` |
| `render_building_backdrop.py` | Building-height raster → `data/buildings_{light,dark}.png`, projected to match `template.html`'s own map projection |
| `build_map.py` | Fills the template's placeholders, writes `dist/milan_heat_map.html` |
