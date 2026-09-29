# Milan Heat Exposure — Data Decisions Log

Branch: `milan-heat-exposure`. Extends the original Transit Heat Exposure scope
(see `SCOPO_transitheatvalencia.md`, written for Valencia) to Milan, on a
separate branch — Valencia's `main` stays untouched and green.

This log records every data-sourcing decision, why it was made, and what was
ruled out. Purpose: so the eventual public README can state trade-offs
honestly instead of presenting the final pipeline as if it were the only
option considered.

---

## 1. GTFS (transit schedule data)

**Source:** ATM Milano, via Comune di Milano open data (dataset DS929,
`dati.comune.milano.it/gtfs.zip`; licence as stated on the DS929 page —
check it before publishing). The version used is the archived **feed v417**
(`feed_start_date` 2026-06-08, end 2026-07-05, which covers the study day
June 28), downloaded from the Mobility Database (mobilitydatabase.org,
source id 2666, snapshot 2026-06-11) into `data_milan/raw/gtfs/` — not
versioned, see §7.

**Not evaluated as an issue:** unlike Valencia (EMT + GVA, two feeds with
different schemas), Milan is a single clean agency feed. This means the
project loses some of the "messy multi-source normalization" story that
Valencia's dbt project demonstrates — a real trade-off, not something to
paper over. If that matters later, a second Milan-area network (e.g.
Trenord) could be added, but it's out of scope for now (see "Disciplina di
scope" in the original document).

## 2. Building height (for solar shadow geometry)

**Ruled out: Regione Lombardia LiDAR.** Access is restricted to Lombard
public administrations or professionals under contract with one — not
available for a personal project. Verified via the Geoportale della
Lombardia's own request process (PEC-only request form).

**Considered: OSM `building:levels`.** The declared fallback in the original
scope document. Literature review (peer-reviewed study on OSM completeness
in Italy) confirms coverage is uneven: good in historic centers, patchy in
suburbs/industrial areas. Usable, but with real gaps to manage.

**Chosen: Copernicus Urban Atlas — Building Height 2012.** Free, open
license, 10m resolution raster, covers ~870 European cities including
Milan. Same spatial resolution class as the PNOA LiDAR used for Valencia,
without Lombardy's access restriction.

- File: `data_milan/seeds/building_height/IT002_MILANO_UA2012_DHM_V010.tif`
- CRS: EPSG:3035 (needs reprojection to WGS84 to join with GTFS stop coords)
- Resolution: 10m, uint16, nodata=65535
- Value range: 3–125 (meters), mean 9.96m over building pixels
- 91.8% nodata pixels — expected, most of the bounding box isn't building
  footprint
- Reference year: 2012 — a real limitation, declared: Milan's building stock
  has changed since (e.g. skyline development at Porta Nuova/CityLife
  post-dates this data). Building heights change slowly enough for most of
  the city fabric that this is an acceptable approximation, but it should be
  named as a limitation, not hidden.

## 3. Shelter / shade at the stop itself

**Not in the original Valencia scope** — added after reviewing the shadow
model: building height alone only captures the "urban canyon" effect and
misses two things that often matter more at a single stop: street trees and
the stop's own shelter structure.

**Ruled out: tree canopy (OSM `natural=tree`, `landuse=forest`).** Even
patchier than `building:levels` for individual street trees — risk of
adding noise rather than signal. Not used.

**Chosen: OSM `shelter` tag on bus stop nodes.** Verified via Overpass API
(query run by the user via overpass-turbo.eu, since this sandbox's network
policy blocks Overpass endpoints directly):

- 2,931 stops (`highway=bus_stop` + `public_transport=platform`) in Milan
- 2,833 (96.7%) have the `shelter` tag populated at all (yes or no) — likely
  a bulk import of ATM's own stop inventory into OSM, not organic tagging
- 1,600 (54.6%) have `shelter=yes`
- File: `data_milan/seeds/osm_shelter/export_shelter_milano.geojson`

This is the most direct, most reliable signal in the whole dataset — more so
than inferring shade from building geometry — and will be used as a second
input layer alongside the building-height-based shadow calculation, not a
replacement for it.

## 4. Shadow-casting method

**Considered: ShadeMap (shademap.app).** Found while discussing feasibility.
Free tier exists (1-3m accuracy, volunteer/estimated data); a paid tier uses
real LiDAR (0.25m). A third-party tool (`U-Shift/shademap-download-tool`,
a transport research group at Técnico Lisboa) can export shadow layers from
it as GeoTIFF over a custom area.

**Ruled out for the pipeline itself:** no clear terms of use found for
redistribution/reuse of derived data. For a project that has to stay
reproducible via `git clone` + a documented setup — the same bar the
Valencia repo holds itself to — depending on a third-party service with
unclear licensing is a real risk, not a hypothetical one. May still be used
informally for visual sanity-checking of our own output, never as a data
source in the script.

**Chosen: compute it ourselves**, using the Urban Atlas raster (§2) and
solar position geometry (library TBD — pysolar or pvlib). Full control, no
external dependency, consistent with the project's existing "no unnecessary
external dependencies" stance (already applied to `dbt_utils` in the
Valencia repo).

**Open commitment:** since this is a simplified model (not full 3D city
massing), the script needs to report an estimated error margin against a
more accurate method — not just produce a number with no sense of its own
uncertainty. To be done when the script is written.

## 5. Critical time window (which hours/days to compute at all)

**Why this exists:** the original scope said "one summer month" as a
placeholder. Milan gave the opportunity to base this on real, documented
heat rather than an arbitrary window.

**Source:** ARPA Lombardia, "Dati sensori meteo" open dataset
(`dati.lombardia.it`, dataset `647i-nhxk`) — blocked by this sandbox's
network policy like every other government portal touched in this project;
downloaded manually by the user and uploaded here.

**Stations used:** all 6 temperature sensors located inside Milan city
(from the companion "Stazioni Meteorologiche — provincia Milano" dataset),
not just one — deliberately, to capture intra-urban variability:

| IdSensore | Station | % readings >30°C (May–Sep 2026) |
|---|---|---|
| 2001 | Milano Lambrate | 23.9% |
| 5897 | Milano v.Brera | 27.3% |
| 5909 | Milano v.Juvara | 28.6% |
| 5911 | Milano v.Marche | 28.9% |
| 5920 | Milano P.zza Zavattari | 35.2% |
| 8162 | Milano v.Feltre | 22.6% |

**Period: 2026 only, May 1 – Sep 9 (data availability cutoff).** Deliberate,
not a shortcut: 2026 is documented (ARPA Lombardia, widely reported) as
Milan/Lombardy's hottest summer since 1951. Using it means the project can
honestly claim to study a specific, well-documented extreme event — not a
"typical Milan summer," which one year of data couldn't support claiming
anyway. Multi-year comparison was considered and set aside as unnecessary
scope for what the project is trying to show (see "Disciplina di scope").

Files: `data_milan/seeds/weather/arpa_lombardia_temp_2026_raw.csv` (as
downloaded, 10-minute readings) and `..._clean.csv` (parsed dates/values,
station names joined in).

### Time base: ARPA hours are solar time (UTC+1)

The ARPA dataset "Dati sensori meteo" (dati.lombardia.it 647i-nhxk)
declares its timestamps in **solar time (UTC+1)**, not in CEST (UTC+2,
daylight saving). The `hour` column of `arpa_lombardia_temp_2026_clean.csv`
was taken from the timestamp without conversion, so it is **ARPA solar
time**; the CSVs are not regenerated. The empirical window "12–18" is
therefore **13–19 CEST**, and that is what the solar and wait analyses use
(`arpa_solar_to_cest()` in `solar_exposure.py`: +1 h). An earlier version
used 12–18 as CEST, a one-hour shift, now fixed.

### Findings — critical hours

% of all readings (6 stations, full period) exceeding 30°C, by hour of day:

| Hour (ARPA solar) | % >30°C | | Hour (ARPA solar) | % >30°C |
|---|---|---|---|---|
| 11 | 44.7 | | 15 | 64.4 |
| **12** | **54.6** | | 16 | 64.2 |
| 13 | 61.4 | | **17** | **62.3** |
| **14** | **64.9 (peak)** | | 18 | 55.8 |

Same table in CEST: 12→13:00, 13→14:00, **14→15:00 (peak)**, 15→16:00,
16→17:00, 17→18:00, 18→19:00.

**Critical window: 12:00–18:00 in ARPA time, i.e. 13:00–19:00 CEST**, core
13:00–17:00 ARPA (>60% of readings over threshold). This empirically confirms the standard climatological
assumption for this latitude/climate, but now it's backed by this specific
summer's actual station data rather than assumed.

### Findings — critical days

Using the average of all 6 stations' daily maximum (a city-wide estimate,
not a single reference station):

- **97 of 132 days** (May 1–Sep 9) had a city-average daily max >30°C
- One continuous window: **June 13 – August 20 (69 days)**
- Two shorter windows not mentioned in press coverage: **May 23–June 1**
  and **August 26–September 8**
- Hottest day: **June 28, city average 38.2°C**
- Absolute peak reading: **39.86°C, July 31 at 13:30** (v.Juvara or similar
  — higher than the 37.8°C city-wide figure ARPA/press reported, plausible
  local urban-heat-island variability between stations)

**Discrepancy vs. press coverage, understood and documented, not hidden:**
news coverage (citing ARPA) described *two* separate heat waves (June
13–July 19, then July 25–August 20), implying a cooler gap July 20–24. Our
6-station average shows no such gap — the window is continuous. Checking
per-station data explains why: `v.Brera` (likely the single reference
station behind the press figure) dips just under 30°C on exactly those
days (29.4–29.9°C), while `P.zza Zavattari` stays above 32°C throughout.
**The "two waves" framing is a single-station artifact; averaging across
stations erases it.** This is a genuine, citable finding of this project's
own analysis, not a reproduction of the press narrative — worth keeping
visible in the final README rather than smoothing it away.

---

## 6. Shadow-casting implementation and its error margin

**Script:** `scripts/milan/solar_exposure.py`, tested by
`scripts/milan/test_solar_exposure.py` (12 tests, all passing).

**Method:** for each stop and each hour, get sun azimuth/elevation via
`pysolar`, then march from the stop toward the sun over the building-height
raster (reprojected stop coordinates via `pyproj`, EPSG:4326 → EPSG:3035)
in 10m steps up to a per-hour radius (see below). At each step, a building is
considered tall enough to cast a shadow back to the stop if its height
exceeds `distance * tan(solar elevation)`. First hit along the ray wins.

**Study date:** June 28, 2026 — the hottest day found in §5, not an
arbitrary solstice pick. Hours: 13:00–19:00 CEST, i.e. the ARPA solar-time
window 12–18 from §5 converted to local clock time.

**Search radius (no fixed cap):** for each hour the march goes out to
`max raster height / tan(elevation)`, rounded up to the next 10m step
(`search_radius_for()`). The raster's tallest building is 125m, so no
building can cast a shadow beyond that radius and truncation misses
nothing. The previous fixed 80m cap could miss shadows at 17:00 and 18:00.
Radius per hour, printed by the script:

| Hour | Elevation | Search radius |
|---|---|---|
| 13:00 | 67.2° | 60m |
| 14:00 | 66.8° | 60m |
| 15:00 | 60.8° | 70m |
| 16:00 | 51.9° | 100m |
| 17:00 | 41.8° | 140m |
| 18:00 | 31.3° | 210m |
| 19:00 | 20.9° | 330m |

(The old fixed 80m cap would have missed shadows from 17:00 on.)

**Result on the real data (2,931 stops × 7 hours = 20,517 rows):**

- % of (stop, hour) pairs exposed (no shadow, no shelter): 34.9% overall
  (42.6% at 13:00 down to 22.2% at 19:00)
- Physically sane pattern: only 4.9–5.4% of stops are in building shadow at
  solar noon (13:00–14:00, sun nearly overhead → short shadows), rising to
  32.5% at 18:00 and 46.6% at 19:00 (low sun → long shadows) — the model responds to solar
  geometry the way it should, not noise
- **562 stops (19%) are exposed at every one of the 7 hours** — never
  shadowed by a building, never sheltered. These are the actionable
  finding: candidates for shelter/shade investment.
- 1,624 stops (55%) are never exposed in the window (shadowed at some
  point, sheltered, or both)

Output seed: `data_milan/seeds/stop_solar_exposure.csv` (columns: stop_id,
hour, solar_azimuth, solar_elevation, in_building_shadow, has_shelter,
exposed).

### 6.1 Sensitività al fattore pensilina (T13)

La metrica corretta è **minuti di attesa al sole diretto**, non un indice di
stress termico: il modello conta ombra, pensilina e sole, non temperatura
dell'aria, umidità né irraggiamento riflesso. `shelter_exposure_factor` (0,5)
è una scelta, non una misura, quindi `mart_stop_heat_risk_sensitivity` ricalcola
`exposure_score_hours` e `risk_level` per ogni fattore in `shelter_factor_grid`
(0; 0,25; 0,5; 0,75; 1; 1,2), stesse soglie (high >= 5, low <= 1). Un fattore
> 1 rappresenta una pensilina chiusa che peggiora lo stress rispetto al sole
aperto (ritenzione di calore e radiazione riflessa: Lanza et al. 2025; anche
Ernst, Watkins e Chen 2025, Transportation Research Part D 140, 104653).

Fermate con `risk_level` alto: 941 con fattore 0, 941 con 0,5, 2.212 con 1 e
con 1,2 (basso: 1.657, 155, 89 e 73). **1.347 fermate (46%) restano nella stessa
classe per ogni fattore, 1.584 (54%) no**; tra fattore 0 e 1,2 cambiano classe
tutte e 1.584 le instabili (la classe è monotona nel fattore). Le colonne
`risk_level_stable` e `exposure_decile` (10 = più esposte, decili di
`exposure_score_hours`) sono in `mart_stop_heat_risk` e nei mart che ne derivano.
Le fermate instabili "dipendono dalla pensilina" e vanno lette con cautela.

## Still open

- ~~Whether shelter and building shadow should be read separately~~ —
  decided: a shelter is an attenuating factor, not a full cancel. A roof
  in full sun does not cool like a building's (or a tree's) shade, so a
  sheltered stop-hour in the sun scores `shelter_exposure_factor` (0.5)
  instead of 0; building shadow stays 0, unsheltered sun stays 1. The
  binary `exposed` flag in the seed is kept for comparison (§8).
- Whether the critical-day windows found in §5 change which GTFS service
  dates get joined against (`mart_service_frequency` in the Valencia repo
  is day-type based, not exact-date — Milan's mart may want the actual June
  28 service pattern specifically, which needs a different join)
- This is a single representative day (June 28), not the full June
  13–August 20 window — a real simplification consistent with the
  project's "declared v1 approximation" pattern (same spirit as Valencia's
  headway-based wait time), but worth being explicit that "hottest day"
  ≠ "every hot day"

## 7. Wait time per stop (evolutivo, not merged into the exposure signal)

Added on request, kept deliberately separate — a different question
("how long do I wait") from exposure ("am I in the sun"), and a different
underlying dataset (GTFS `stop_id`, not the OSM nodes used for shelter/
shadow), so it's its own script, its own seed, and its own map rather than
a new column bolted onto `stop_solar_exposure.csv`.

**Script:** `scripts/milan/wait_time.py`. **Seed:**
`data_milan/seeds/stop_wait_time.csv` (28,911 stop×hour rows, 4,246 distinct
GTFS stops; median wait 9.8 min).

**Reference day: June 28 2026, the same day as the exposure analysis (§6).**
The ATM GTFS feed is version 417 (Mobility Database, dated 2026-06-11),
valid 2026-06-08 to 2026-07-05, with 118 active service_ids on 2026-06-28
(a Sunday, full coverage like the other Sundays). Hours 13–19 CEST, same
window as the exposure. *Superseded:* an earlier version used the
September 13 feed as a stand-in day because June was missing; that
approximation is gone, exposure and wait now refer to the same day.

**Method, precise over cheap (the project owner's explicit choice over a
cheaper combined-schedule shortcut):**
1. Per (stop, route, hour): sort that route's scheduled departures at that
   stop; take the **median** interval between consecutive departures whose
   first departure falls in the hour; halve it (headway/2 — the same
   random-arrival assumption already used for Valencia, not a new one).
2. Per (stop, hour): the **median across every route serving that stop**
   in that hour of step 1's value — answers "how long do I wait for *my*
   line," not "how long until any vehicle regardless of line."
3. Gaps longer than 3 hours are dropped before the median: almost always
   the last trip of the day for that route, not a real headway — keeping
   them in would make a low-frequency line's evening wait look far worse
   than any rider actually experiences.

**Sanity check:** Duomo M1/M3 (a major two-line interchange) comes out to
7–9 minutes across the afternoon — right for Sunday metro frequency.

**ID-space gap, now bridged in dbt:** GTFS `stop_id` and the OSM node ids
used for the exposure map are two different ID spaces — this map still
plots GTFS's own 4,246 stops (metro, tram, bus) at GTFS's own coordinates,
independently of the 2,931 OSM stops in the exposure map. The two are
reconciled in the dbt layer (`int_osm_gtfs_stop_bridge`, §8), not here.
Nearest-point alone turned out to be the weaker key: most OSM stops carry
a `ref` tag equal to ATM's GTFS `stop_id`, and nearest-point agrees with it
only ~92% of the time, so `ref` comes first and proximity is the fallback.

**Visualization:** blue-to-violet sequential ramp (the project owner's
request), capped at 25 minutes for color purposes — a handful of
low-frequency stops wait up to ~81 minutes, and letting that outlier set
the top of the scale would wash out the difference between everyone else.
No building-height backdrop on this map yet (different, larger bounding
box than the exposure map's OSM stops — the backdrop image would need
regenerating at that extent, not reused as-is).

### 7.1 Modello misto, limiti inferiore e superiore (T12)

Headway/2 vale solo con arrivi davvero casuali. Con servizi poco frequenti
molti passeggeri guardano l'orario e arrivano poco prima della corsa, quindi
l'attesa vera è più bassa. Il seed ora ha, oltre a `median_wait_minutes`
(invariata, H/2 con H = headway mediano tra le linee):
`median_headway_minutes` (H), `wait_any_line_minutes` (tutte le partenze di
tutte le linee alla fermata, ordinate; sugli intervalli consecutivi 0 < H < 3 h
con prima partenza nell'ora, attesa casuale E[H²]/(2·E[H]) = E[H]/2·(1+CV²),
Osuna e Newell 1972) e `wait_least_frequent_minutes` (max tra le linee di
headway/2).

**Modello misto** (`int_stop_wait_time`, Luethi et al. 2007 per l'idea di una
quota di passeggeri sincronizzati): quota sincronizzata s = 0 per H ≤ 5 min,
lineare fino a `sync_share_max` per H = 11 min, costante oltre (transizione
casuale/non casuale tra 5 e 11 min: Singh, Graham, Hörcher, Anderson 2021,
Transportation Research Part C 130; Ingvardson et al. 2018, Transportation
Research Part C). Attesa = (1−s)·H/2 + s·min(H/2, `sync_wait_minutes`).
**Parametri, ipotesi e non misure:** `sync_share_max` = 0,5 e
`sync_wait_minutes` = 2 min (var dbt in `dbt_project.yml`, modificabili con
`--vars` per la sensitività). Le fonti danno la forma della transizione, non
questi due valori.

**Limiti** in `mart_stop_heat_wait_hourly`: `wait_minutes_low` =
min(attesa qualsiasi linea, misto); `wait_minutes_high` = linea meno frequente;
`wait_minutes_random` = vecchia stima H/2. Ordine atteso low ≤ misto ≤ random ≤
high, verificato da un test (tolleranza 0,06 min per l'arrotondamento a un
decimale di `median_wait_minutes`). `wait_time_bucket` ora si calcola sul misto.

**Numeri** (fermate abbinate, 18.226 stop-ora con servizio): mediana attesa
casuale 9,0 min contro 5,5 min misto; mediane low 5,3 e high 9,5 (su tutte le
stop-ora del mart). Il 93,8% delle stop-ora ha H ≥ 11 min, cioè s = s_max:
di domenica pomeriggio il servizio è raro, quindi il risultato dipende molto
da `sync_share_max`. `avg_exposed_wait_minutes` mediano per le fermate a
rischio alto: 5,25 min (era 8,6 con l'attesa casuale).

**Sensitività a `sync_share_max`** (`mart_heat_wait_sensitivity`, misto
ricalcolato con `sync_share_grid`; mediana / p90 di `avg_exposed_wait_minutes`,
minuti di attesa al sole diretto, non un indice di stress termico):

| sync_share_max | alto (795 fermate) | medio (1.692) | basso (140) |
|---|---|---|---|
| 0 | 8,61 / 11,41 | 3,96 / 5,88 | 1,18 / 1,64 |
| 0,25 | 6,91 / 9,06 | 3,21 / 4,66 | 0,96 / 1,30 |
| 0,5 (default) | 5,25 / 6,71 | 2,44 / 3,43 | 0,73 / 0,96 |
| 0,6 | 4,59 / 5,76 | 2,15 / 2,97 | 0,64 / 0,83 |

Il valore cambia di circa il 47% fra 0 e 0,6 per il rischio alto: l'ordine dei
livelli resta, ma l'entità assoluta dipende da un'ipotesi.

## 8. dbt layer

**Ingestion:** `ingestion/load_milan.py`, mirroring `load_gtfs.py`'s
pattern — loads the two CSVs from §6/§7 into a `raw_milan` schema. Unlike
`raw_emt`/`raw_gva`, these aren't a raw GTFS extract, they're already
computed by the two Python scripts, so there's no `data_milan/raw/`
equivalent to `data/raw/` and no per-agency file list to iterate.

**Models** (`models/staging/milan/`, `models/intermediate/`, `models/marts/`):

- `stg_stop_solar_exposure` — cast/rename over `raw_milan.stop_solar_exposure`.
  Renames `stop_id` to `osm_node_id` here rather than leaving it generic,
  so the ID-space split from §7 is visible in the schema itself, not just
  in this doc.
- `int_stop_wait_time` — reads `raw_milan.stop_wait_time` directly (no
  staging layer: the source CSV is already a computed metric, not a raw
  extract needing normalization). Adds `wait_time_bucket`
  (low/medium/high, split at the same 10/25-minute marks the map's colour
  ramp uses).
- `mart_stop_heat_risk` — grain change from `stg_stop_solar_exposure`
  (stop × hour) to stop. Per hour, `exposure_score` (in staging) is 0 in
  building shadow, `var('shelter_exposure_factor', 0.5)` in the sun under a
  shelter, 1 in unsheltered sun (see "Still open", decided). The mart sums
  it to `exposure_score_hours` (0–7) and `risk_level` (`high` ≥ 5, `low`
  ≤ 1, else `medium`): 941 high / 1,835 medium / 155 low. The original
  binary reading is kept as `hours_exposed_binary` / `risk_level_binary`
  (`high` = exposed all 7 hours — the 562-stop finding from §6).
- `mart_stop_heat_wait_hourly` — stop × hour (20,517 rows), the map's
  data source; columns fixed by `contract/map_data.md`.
- `int_osm_gtfs_stop_bridge` — one row per OSM stop (from the OSM export,
  loaded as `raw_milan.osm_shelter_stops`). `match_method`: `ref` when the
  OSM `ref` tag equals a GTFS `stop_id` within 200 m (sanity cap against
  stale tags); otherwise `nearest` = closest GTFS stop within 30 m (tie-break
  on `stop_id`); otherwise `unmatched`. Distances are haversine in plain SQL
  (`macros/haversine_distance_m.sql`, no spatial extension). Result:
  2,511 `ref` (median 8.6 m), 116 `nearest` (median 14.8 m), 304
  `unmatched` (10.4%).
- `mart_stop_heat_wait` — `mart_stop_heat_risk` + bridge + wait time, per
  OSM stop. `avg_exposed_wait_minutes` = mean, over the hours with service,
  of (hourly `exposure_score` × that hour's median wait), taken from
  `mart_stop_heat_wait_hourly` — the same definition the map uses, pinned
  by `assert_heat_wait_avg_matches_hourly.sql`: average minutes a passenger
  waits in the sun. Median 8.6 min for `high`-risk stops (p90 11.4), 4.0
  for `medium`, 1.2 for `low`. Exposure and wait both refer to June 28
  2026 (feed v417).
- Tests: `not_null`/`accepted_values` on hour and bucket/risk columns, plus
  a singular uniqueness test (`assert_stg_stop_solar_exposure_unique_node_hour.sql`,
  mirroring `assert_fct_trips_unique_trip_date.sql`'s pattern) and
  `unique`/`not_null` on `mart_stop_heat_risk.osm_node_id`. All pass;
  `mart_stop_heat_risk`'s risk_level_binary counts (562 high / 745 medium /
  1,624 low) match §6's findings exactly; `assert_exposure_score_valid.sql`
  pins the hourly score to {0, factor, 1}.

## 9. Running it

Uses a separate virtualenv from Valencia (`.venv-milan`): rasterio,
pyproj, and pysolar aren't needed there.

```bash
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
print(con.execute('select risk_level, count(*) from main.mart_stop_heat_risk group by 1').fetchall())  # weighted; risk_level_binary for the §6 reading
"
```

**Map tool** (optional — separate deps, see
[`scripts/milan/map/README.md`](../scripts/milan/map/README.md) for the
full pipeline and its known deferred aesthetic issues):

```bash
cd scripts/milan/map
python prepare_exposure_data.py && python prepare_wait_data.py \
  && python render_building_backdrop.py && python build_map.py
# -> dist/milan_heat_map.html, open directly in a browser
```
