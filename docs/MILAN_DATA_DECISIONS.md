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

- dbt layer: `stg_stop_solar_exposure`, `int_stop_wait_time`,
  `mart_stop_heat_risk` from the original scope are not yet written — the
  seed above is ready to be the source for them
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
