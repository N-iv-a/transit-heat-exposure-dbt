{#
  Grain: one row per osm_node_id (2,931 rows) -- same fields as
  mart_stop_heat_risk plus the bridge to the GTFS wait-time side
  (int_osm_gtfs_stop_bridge.sql), for stops that could be matched.

  avg_exposed_wait_minutes is the mean, over the 7 critical hours
  (12:00-18:00), of (exposed ? median_wait_12_18 : 0) -- i.e. average
  minutes spent waiting in direct sun per hour of the window, treating
  unexposed hours as contributing 0. It's NULL when the stop has no GTFS
  match (match_method = 'unmatched') or the matched GTFS stop has no wait
  data in the 12-18 window.

  Reminder (see int_osm_gtfs_stop_bridge.sql): exposure is for 2026-06-28,
  wait time for 2026-09-13 -- two different reference days, combined here
  only through the stop identity, not the calendar date.
#}

with heat_risk as (

    select
        osm_node_id,
        hours_measured,
        hours_exposed,
        pct_hours_exposed,
        has_shelter,
        risk_level

    from {{ ref('mart_stop_heat_risk') }}

),

bridge as (

    select osm_node_id, gtfs_stop_id, match_method, distance_m
    from {{ ref('int_osm_gtfs_stop_bridge') }}

),

wait_12_18 as (

    select
        gtfs_stop_id,
        median(median_wait_minutes) as median_wait_12_18

    from {{ ref('int_stop_wait_time') }}
    where hour between 12 and 18
    group by 1

),

exposure_hours as (

    select osm_node_id, hour, exposed
    from {{ ref('stg_stop_solar_exposure') }}

),

exposed_wait_hours as (

    select
        e.osm_node_id,
        e.hour,
        case when e.exposed then w.median_wait_12_18 else 0 end as exposed_wait_minutes

    from exposure_hours e
    inner join bridge b on e.osm_node_id = b.osm_node_id
    inner join wait_12_18 w on b.gtfs_stop_id = w.gtfs_stop_id

),

avg_exposed_wait as (

    select osm_node_id, avg(exposed_wait_minutes) as avg_exposed_wait_minutes
    from exposed_wait_hours
    group by 1

)

select
    hr.osm_node_id,
    hr.hours_measured,
    hr.hours_exposed,
    hr.pct_hours_exposed,
    hr.has_shelter,
    hr.risk_level,
    b.gtfs_stop_id,
    b.match_method,
    b.distance_m,
    w.median_wait_12_18,
    aew.avg_exposed_wait_minutes

from heat_risk hr
left join bridge b on hr.osm_node_id = b.osm_node_id
left join wait_12_18 w on b.gtfs_stop_id = w.gtfs_stop_id
left join avg_exposed_wait aew on hr.osm_node_id = aew.osm_node_id
