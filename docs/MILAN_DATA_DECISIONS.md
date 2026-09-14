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

**Source:** ATM Milano, via Comune di Milano open data
(`dati.comune.milano.it/gtfs.zip`) — already in hand, no blocker.

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

### Findings — critical hours

% of all readings (6 stations, full period) exceeding 30°C, by hour of day:

| Hour | % >30°C | | Hour | % >30°C |
|---|---|---|---|---|
| 11 | 44.7 | | 15 | 64.4 |
| **12** | **54.6** | | 16 | 64.2 |
| 13 | 61.4 | | **17** | **62.3** |
| **14** | **64.9 (peak)** | | 18 | 55.8 |

**Critical window: 12:00–18:00**, core 13:00–17:00 (>60% of readings over
threshold). This empirically confirms the standard climatological
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
`scripts/milan/test_solar_exposure.py` (7 tests, all passing).

**Method:** for each stop and each hour, get sun azimuth/elevation via
`pysolar`, then march from the stop toward the sun over the building-height
raster (reprojected stop coordinates via `pyproj`, EPSG:4326 → EPSG:3035)
in 10m steps up to `SEARCH_RADIUS_M = 80`. At each step, a building is
considered tall enough to cast a shadow back to the stop if its height
exceeds `distance * tan(solar elevation)`. First hit along the ray wins.

**Study date:** June 28, 2026 — the hottest day found in §5, not an
arbitrary solstice pick. Hours: 12:00–18:00 local (CEST), matching the
empirical critical window from §5.

**Error margin, computed and printed by the script itself, not asserted
after the fact:**

| Hour | Elevation | Max height missable beyond 80m |
|---|---|---|
| 12:00 | 61.7° | 149m |
| 13:00 | 67.2° | 190m |
| 14:00 | 66.8° | 187m |
| 15:00 | 60.8° | 143m |
| 16:00 | 51.9° | 102m |
| 17:00 | 41.8° | 71m |
| 18:00 | 31.3° | 49m |

The raster's tallest building is 125m. So for 12:00–16:00, the truncation
at 80m cannot miss anything in this dataset — the required height to be
missed already exceeds what exists. Real (bounded) risk of under-detecting
shadow starts at 17:00 (buildings >71m beyond 80m) and is largest at 18:00
(buildings >49m beyond 80m). This is a declared limitation of the last two
hours in the window, not the whole result.

**Result on the real data (2,931 stops × 7 hours = 20,517 rows):**

- % of (stop, hour) pairs exposed (no shadow, no shelter): 37.4% overall
- Physically sane pattern: only 4.9–5.4% of stops are in building shadow at
  solar noon (13:00–14:00, sun nearly overhead → short shadows), rising to
  32.4% by 18:00 (low sun → long shadows) — the model responds to solar
  geometry the way it should, not noise
- **724 stops (25%) are exposed at every one of the 7 hours** — never
  shadowed by a building, never sheltered. These are the actionable
  finding: candidates for shelter/shade investment.
- 1,612 stops (55%) are never exposed in the window (shadowed at some
  point, sheltered, or both)

Output seed: `data_milan/seeds/stop_solar_exposure.csv` (columns: stop_id,
hour, solar_azimuth, solar_elevation, in_building_shadow, has_shelter,
exposed).

## Still open

- How exactly `shelter` and building-shadow layers combine into one
  exposure signal is already answered by the script (both must be absent
  for "exposed" to be true) — but whether the mart should also expose them
  separately (for a "how much does shelter alone change things" cut) isn't
  decided yet
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
`data_milan/seeds/stop_wait_time.csv` (28,655 stop×hour rows, 4,192 distinct
GTFS stops).

**Reference day, again not June 28 itself.** The ATM GTFS feed is a
present-plus-near-future snapshot (`feed_start_date` 2026-08-31) and simply
doesn't contain June's schedule. June 28 2026 was a Sunday, so **September
13, 2026** — a Sunday fully inside the feed's well-covered window (118
active service_ids, versus just 5 for dates from Sep 14 on, which are
clearly not representative) — stands in as the day-type. Confirmed
acceptable: service patterns don't shift much over a few months when
schools are still in session, which they were in both June and this
September window.

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

**Known gap, same shape as the shelter/shadow ID mismatch:** GTFS `stop_id`
and the OSM node ids used for the exposure map are two different ID spaces
with no shared key, and no join was attempted — this map plots GTFS's own
4,192 stops (metro, tram, bus) at GTFS's own coordinates, independently of
the 2,931 OSM stops in the exposure map. Reconciling them (nearest-point
match) is a fair next step if the two are ever meant to be read together,
not assumed here.

**Visualization:** blue-to-violet sequential ramp (the project owner's
request), capped at 25 minutes for color purposes — a handful of
low-frequency stops wait up to ~81 minutes, and letting that outlier set
the top of the scale would wash out the difference between everyone else.
No building-height backdrop on this map yet (different, larger bounding
box than the exposure map's OSM stops — the backdrop image would need
regenerating at that extent, not reused as-is).

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
  (stop × hour) to stop: `hours_exposed`, `pct_hours_exposed`, and a
  `risk_level` flag (`high` = exposed at all 7 hours — the 724-stop
  actionable finding from §6). Deliberately does not join
  `int_stop_wait_time` in: the two models key off different ID spaces
  (OSM node id vs. GTFS `stop_id`), so heat risk and wait time stay two
  separate marts, matching the two separate maps, rather than forcing a
  join that would silently drop or duplicate rows.
- Tests: `not_null`/`accepted_values` on hour and bucket/risk columns, plus
  a singular uniqueness test (`assert_stg_stop_solar_exposure_unique_node_hour.sql`,
  mirroring `assert_fct_trips_unique_trip_date.sql`'s pattern) and
  `unique`/`not_null` on `mart_stop_heat_risk.osm_node_id`. All pass;
  `mart_stop_heat_risk`'s risk_level counts (724 high / 595 medium / 1,612
  low) match §6's findings exactly.
