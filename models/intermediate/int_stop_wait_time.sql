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
#}

select
    stop_id as gtfs_stop_id,
    stop_name,
    lat,
    lon,
    cast(hour as integer) as hour,
    median_wait_minutes,
    cast(n_lines as integer) as n_lines,
    case
        when median_wait_minutes is null then null
        when median_wait_minutes >= 25 then 'high'
        when median_wait_minutes >= 10 then 'medium'
        else 'low'
    end as wait_time_bucket

from {{ source('raw_milan', 'stop_wait_time') }}
