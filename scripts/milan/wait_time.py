"""Compute median expected wait time per Milan GTFS stop, per hour band
(13:00-19:59 CEST, one bucket per clock hour), for Sunday June 28 2026.

Reference day: Sunday June 28 2026, the same day as the solar exposure
analysis. The ATM GTFS feed is version 417 (Mobility Database, dated
2026-06-11), valid 2026-06-08 to 2026-07-05, with 118 active service_ids
on that date (full coverage, like the other Sundays in the feed). Hours are
CEST clock hours 13-19, matching the exposure window (= ARPA 12-18 in solar
time).

Method (per the project owner's choice — precise over cheap):
  1. Per (stop, route, hour): the scheduled departures for that route at
     that stop are sorted; the wait is estimated from the MEDIAN interval
     between consecutive departures whose first departure falls in that
     hour, halved (average wait under random passenger arrival — the same
     headway/2 assumption already used in the Valencia project's design).
  2. Per (stop, hour): the median of that value ACROSS the routes serving
     the stop in that hour — not a combined-schedule estimate. More
     expensive, but answers "how long do I wait for MY bus," which is
     what a rider actually experiences, not "how long until any vehicle."

Extra columns (T12, see docs/MILAN_DATA_DECISIONS.md section 7):
  - median_headway_minutes: the median across routes of the per-route median
    headway (median_wait_minutes is this / 2, up to rounding).
  - wait_any_line_minutes: all departures of all routes at the stop are
    merged and sorted; over the consecutive intervals H whose first
    departure falls in the hour, the wait for random arrivals is
    E[H^2] / (2 E[H]) = E[H]/2 * (1 + CV^2) (Osuna and Newell 1972). Same
    filters (0 < H < 3 h). Lower bound: a rider who takes any line.
  - wait_least_frequent_minutes: max across routes of headway/2. Upper
    bound: a rider who needs the least frequent line.

  - n_departures (T16): number of stop_times rows (all routes) of the trips
    active on the reference day whose departure hour bucket is the hour.
    Supply proxy, not demand. Rows exist for every (stop, hour) with at least
    one departure; where no wait is computable (e.g. a single departure)
    the wait columns are empty and n_lines is 0.

Gaps longer than 3 hours are dropped before computing the median: those
are almost always the last trip of the day for a route, not a real
headway, and would otherwise inflate a low-frequency line's evening wait
with a number nobody actually experiences.
"""

from pathlib import Path

import duckdb

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
GTFS_DIR = PROJECT_ROOT / "data_milan/raw/gtfs"
OUTPUT_CSV = PROJECT_ROOT / "data_milan/seeds/stop_wait_time.csv"

REFERENCE_DATE = 20260628  # Sunday, same day as the exposure analysis
MAX_GAP_SECONDS = 3 * 3600  # drop end-of-service gaps, not real headways

QUERY = f"""
with active_services as (
    select service_id
    from read_csv_auto('{GTFS_DIR}/calendar_dates.txt')
    where date = {REFERENCE_DATE} and exception_type = 1
),
trips_active as (
    select t.trip_id, t.route_id
    from read_csv_auto('{GTFS_DIR}/trips.txt') t
    join active_services s using (service_id)
),
departures as (
    select
        st.stop_id,
        ta.route_id,
        st.trip_id,
        cast(split_part(st.departure_time, ':', 1) as integer) as raw_hour,
        cast(split_part(st.departure_time, ':', 1) as integer) * 3600
          + cast(split_part(st.departure_time, ':', 2) as integer) * 60
          + cast(split_part(st.departure_time, ':', 3) as integer) as total_seconds
    from read_csv_auto(
        '{GTFS_DIR}/stop_times.txt',
        types={{'stop_id': 'VARCHAR'}}
    ) st
    join trips_active ta using (trip_id)
    -- a handful of rows in the raw feed carry a stop NAME (e.g. "ABBIATEGRASSO")
    -- instead of a numeric stop_id -- real data quality noise, not a parsing bug.
    -- They won't match any row in stops.txt and are dropped by the later join,
    -- which is the right outcome: better to drop a stop we can't place than to
    -- guess at a location for it.
),
ordered as (
    select
        stop_id, route_id, total_seconds,
        (raw_hour % 24) as hour_bucket,
        lead(total_seconds) over (partition by stop_id, route_id order by total_seconds) as next_seconds
    from departures
),
intervals as (
    select stop_id, route_id, hour_bucket, (next_seconds - total_seconds) as interval_seconds
    from ordered
    where next_seconds is not null
      and hour_bucket between 13 and 19
      and next_seconds > total_seconds
      and (next_seconds - total_seconds) < {MAX_GAP_SECONDS}
),
ordered_all as (
    select
        stop_id, total_seconds,
        (raw_hour % 24) as hour_bucket,
        lead(total_seconds) over (partition by stop_id order by total_seconds) as next_seconds
    from departures
),
intervals_all as (
    select stop_id, hour_bucket,
           (next_seconds - total_seconds) as interval_seconds
    from ordered_all
    where next_seconds is not null
      and hour_bucket between 13 and 19
      and next_seconds > total_seconds
      and (next_seconds - total_seconds) < {MAX_GAP_SECONDS}
),
any_line as (
    select stop_id, hour_bucket,
           avg(interval_seconds * interval_seconds::double)
             / (2.0 * avg(interval_seconds)) / 60.0 as wait_any_line_minutes
    from intervals_all
    group by 1, 2
),
route_headway as (
    select stop_id, route_id, hour_bucket,
           median(interval_seconds) as headway_seconds
    from intervals
    group by 1, 2, 3
),
wait_agg as (
    select
        r.stop_id,
        r.hour_bucket,
        round(median(r.headway_seconds) / 2.0 / 60.0, 1) as median_wait_minutes,
        count(distinct r.route_id) as n_lines,
        round(median(r.headway_seconds) / 60.0, 2) as median_headway_minutes,
        round(any_value(a.wait_any_line_minutes), 2) as wait_any_line_minutes,
        round(max(r.headway_seconds) / 2.0 / 60.0, 2) as wait_least_frequent_minutes
    from route_headway r
    left join any_line a on r.stop_id = a.stop_id and r.hour_bucket = a.hour_bucket
    group by 1, 2
),
dep_counts as (
    select stop_id, (raw_hour % 24) as hour_bucket, count(*) as n_departures
    from departures
    where (raw_hour % 24) between 13 and 19
    group by 1, 2
)
-- every (stop, hour) with at least one departure; wait columns are NULL
-- (n_lines 0) where no wait is computable (e.g. a single departure)
select
    d.stop_id,
    d.hour_bucket as hour,
    w.median_wait_minutes,
    coalesce(w.n_lines, 0) as n_lines,
    w.median_headway_minutes,
    w.wait_any_line_minutes,
    w.wait_least_frequent_minutes,
    d.n_departures
from dep_counts d
left join wait_agg w on d.stop_id = w.stop_id and d.hour_bucket = w.hour_bucket
order by 1, 2
"""


def main() -> None:
    con = duckdb.connect()
    rows = con.execute(QUERY).fetchall()
    cols = [d[0] for d in con.description]
    print(f"{len(rows)} (stop, hour) rows with at least one departure")

    stops = con.execute(
        f"select stop_id, stop_name, stop_lat, stop_lon "
        f"from read_csv_auto('{GTFS_DIR}/stops.txt', types={{'stop_id': 'VARCHAR'}})"
    ).fetchall()
    stop_meta = {r[0]: (r[1], r[2], r[3]) for r in stops}

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    import csv

    with open(OUTPUT_CSV, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["stop_id", "stop_name", "lat", "lon", "hour", "median_wait_minutes", "n_lines",
                         "median_headway_minutes", "wait_any_line_minutes", "wait_least_frequent_minutes", "n_departures"])
        n_written = 0
        for row in rows:
            row_d = dict(zip(cols, row))
            meta = stop_meta.get(row_d["stop_id"])
            if not meta:
                continue
            name, lat, lon = meta
            # 6 decimals ~ 0.1 m: plenty for a stop, and keeps full-precision
            # 15-decimal floats from tripping the phone-number secrets scanner.
            writer.writerow([row_d["stop_id"], name, round(lat, 6), round(lon, 6), row_d["hour"], row_d["median_wait_minutes"], row_d["n_lines"],
                             row_d["median_headway_minutes"], row_d["wait_any_line_minutes"], row_d["wait_least_frequent_minutes"], row_d["n_departures"]])
            n_written += 1

    print(f"Wrote {n_written} rows to {OUTPUT_CSV}")
    waits = [r[2] for r in rows if r[2] is not None]
    if waits:
        waits_sorted = sorted(waits)
        mid = len(waits_sorted) // 2
        print(f"Median wait across all (stop,hour): {waits_sorted[mid]:.1f} min")
        print(f"Max wait: {max(waits):.1f} min, min wait: {min(waits):.1f} min")


if __name__ == "__main__":
    main()
