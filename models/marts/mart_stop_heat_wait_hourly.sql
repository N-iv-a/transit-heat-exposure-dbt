{#
  Main mart behind the map (scripts/milan/map/): one row per
  (osm_node_id, hour), 2,931 OSM stops x 7 hours (13:00-19:00 CEST) = 20,517
  rows. Columns, types and semantics are the contract -- see
  contract/map_data.md, section "main.mart_stop_heat_wait_hourly".

  Two different reference days, combined only through stop identity (see
  int_osm_gtfs_stop_bridge.sql): solar exposure is for 2026-06-28 (the
  hottest day in the ARPA analysis), wait time is for 2026-09-13. A stop
  can have exposure data at every hour but NULL wait_minutes at some (or
  all) hours -- unmatched to GTFS, or matched but with no service running
  at that hour on the wait-time reference day.

  wait_minutes = mixed model (central), _low = min(any-line wait, mixed),
  _high = least frequent line, _random = old headway/2 estimate (T12).

  int_stop_wait_time is one row per (gtfs_stop_id, hour) (verified: no
  duplicates), so the left join below does not fan out exposure rows.
#}

with exposure as (

    select
        osm_node_id,
        hour,
        in_building_shadow,
        in_tree_shadow,
        has_shelter,
        exposure_score

    from {{ ref('stg_stop_solar_exposure') }}

),

shelter_stops as (

    select
        osm_node_id,
        name as stop_name,
        lon,
        lat

    from {{ ref('stg_osm_shelter_stops') }}

),

bridge as (

    select osm_node_id, gtfs_stop_id, match_method
    from {{ ref('int_osm_gtfs_stop_bridge') }}

),

wait_time as (

    select gtfs_stop_id, hour, median_wait_minutes, wait_mixed_minutes,
           wait_any_line_minutes, wait_least_frequent_minutes
    from {{ ref('int_stop_wait_time') }}

),

risk as (

    select osm_node_id, risk_level, risk_level_stable, exposure_decile, tree_shade_hours, n_trees_20m
    from {{ ref('mart_stop_heat_risk') }}

)

select
    e.osm_node_id,
    s.stop_name,
    s.lon,
    s.lat,
    e.hour,
    e.in_building_shadow,
    e.in_tree_shadow,
    e.has_shelter,
    e.exposure_score,
    b.gtfs_stop_id,
    b.match_method,
    w.wait_mixed_minutes as wait_minutes,
    least(w.wait_any_line_minutes, w.wait_mixed_minutes) as wait_minutes_low,
    w.wait_least_frequent_minutes as wait_minutes_high,
    w.median_wait_minutes as wait_minutes_random,
    e.exposure_score * w.wait_mixed_minutes as exposed_wait_minutes,
    r.risk_level,
    r.exposure_decile,
    r.risk_level_stable,
    r.tree_shade_hours,
    r.n_trees_20m

from exposure e
inner join shelter_stops s on e.osm_node_id = s.osm_node_id
inner join bridge b on e.osm_node_id = b.osm_node_id
left join wait_time w on b.gtfs_stop_id = w.gtfs_stop_id and e.hour = w.hour
left join risk r on e.osm_node_id = r.osm_node_id
