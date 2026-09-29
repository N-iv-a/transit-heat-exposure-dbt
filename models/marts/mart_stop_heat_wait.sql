{#
  Grain: one row per osm_node_id (2,931 rows) -- same fields as
  mart_stop_heat_risk plus the bridge to the GTFS wait-time side
  (int_osm_gtfs_stop_bridge.sql), for stops that could be matched.

  avg_exposed_wait_minutes is the average, over the 7 critical hours
  (13:00-19:00 CEST), of exposed_wait_minutes as defined in
  mart_stop_heat_wait_hourly.sql (exposure_score * wait_minutes, the mixed model, for
  that hour -- i.e. the same per-hour definition used by the map), ignoring
  hours with no wait data. It's NULL when the stop has no GTFS match
  (match_method = 'unmatched') or none of the 7 hours has wait data.

  Reminder (see int_osm_gtfs_stop_bridge.sql): exposure is for 2026-06-28,
  wait time for 2026-09-13 -- two different reference days, combined here
  only through the stop identity, not the calendar date.
#}

with heat_risk as (

    select
        osm_node_id,
        hours_measured,
        exposure_score_hours,
        pct_exposure_score,
        hours_exposed_binary,
        pct_hours_exposed_binary,
        has_shelter,
        risk_level,
        risk_level_binary,
        exposure_decile,
        risk_level_stable

    from {{ ref('mart_stop_heat_risk') }}

),

bridge as (

    select osm_node_id, gtfs_stop_id, match_method, distance_m
    from {{ ref('int_osm_gtfs_stop_bridge') }}

),

wait_13_19 as (

    select
        gtfs_stop_id,
        median(median_wait_minutes) as median_wait_13_19

    from {{ ref('int_stop_wait_time') }}
    where hour between 13 and 19
    group by 1

),

hourly as (

    select osm_node_id, exposed_wait_minutes
    from {{ ref('mart_stop_heat_wait_hourly') }}

),

avg_exposed_wait as (

    select osm_node_id, avg(exposed_wait_minutes) as avg_exposed_wait_minutes
    from hourly
    group by 1

)

select
    hr.osm_node_id,
    hr.hours_measured,
    hr.exposure_score_hours,
    hr.pct_exposure_score,
    hr.hours_exposed_binary,
    hr.pct_hours_exposed_binary,
    hr.has_shelter,
    hr.risk_level,
    hr.risk_level_binary,
    hr.exposure_decile,
    hr.risk_level_stable,
    b.gtfs_stop_id,
    b.match_method,
    b.distance_m,
    w.median_wait_13_19,
    aew.avg_exposed_wait_minutes

from heat_risk hr
left join bridge b on hr.osm_node_id = b.osm_node_id
left join wait_13_19 w on b.gtfs_stop_id = w.gtfs_stop_id
left join avg_exposed_wait aew on hr.osm_node_id = aew.osm_node_id
