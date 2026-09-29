{#
  No stg_ layer for this one: stop_wait_time.csv is already a computed
  metric (scripts/milan/wait_time.py -- per-line median headway/2, then
  median across lines serving the stop), not a raw extract that needs
  normalizing. This model just casts types and adds the wait_time_bucket
  used by the map's blue-to-violet ramp (capped at 25 min, same as the
  map -- see docs/MILAN_DATA_DECISIONS.md, section 7).

  stop_id here is a GTFS stop_id, a different ID space from
  stg_stop_solar_exposure's OSM node ids. mart_stop_heat_risk still doesn't
  join the two -- see that model -- but int_osm_gtfs_stop_bridge.sql now
  bridges them for mart_stop_heat_wait.

  Mixed wait model (T12, docs/MILAN_DATA_DECISIONS.md section 7): with
  H = median_headway_minutes, the share s of riders who time their arrival
  to the timetable is 0 for H <= 5, rises linearly to sync_share_max at
  H = 11, and stays there beyond (random/non-random transition between 5
  and 11 min, Singh et al. 2021). Random riders wait H/2, synchronised ones
  least(H/2, sync_wait_minutes):
    wait_mixed_minutes = (1 - s) * H/2 + s * least(H/2, sync_wait_minutes)
  median_wait_minutes (H/2, purely random) is kept for comparison.
#}

with base as (

    select
        stop_id as gtfs_stop_id,
        stop_name,
        lat,
        lon,
        cast(hour as integer) as hour,
        median_wait_minutes,
        cast(n_lines as integer) as n_lines,
        median_headway_minutes,
        wait_any_line_minutes,
        wait_least_frequent_minutes

    from {{ source('raw_milan', 'stop_wait_time') }}

),

with_share as (

    select
        *,
        {{ sync_share('median_headway_minutes', var('sync_share_max', 0.5)) }} as sync_share

    from base

),

mixed as (

    select
        *,
        {{ wait_mixed('median_headway_minutes', 'sync_share', var('sync_wait_minutes', 2)) }}
          as wait_mixed_minutes

    from with_share

)

select
    gtfs_stop_id,
    stop_name,
    lat,
    lon,
    hour,
    median_wait_minutes,
    n_lines,
    median_headway_minutes,
    wait_any_line_minutes,
    wait_least_frequent_minutes,
    sync_share,
    wait_mixed_minutes,
    case
        when wait_mixed_minutes is null then null
        when wait_mixed_minutes >= 25 then 'high'
        when wait_mixed_minutes >= 10 then 'medium'
        else 'low'
    end as wait_time_bucket

from mixed
