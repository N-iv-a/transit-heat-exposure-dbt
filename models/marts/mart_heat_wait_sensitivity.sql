{#
  Sensitivity of the wait to sync_share_max (T13). Grain: one row per
  (sync_share_max, risk_level) = 4 values x 3 levels. For each value in var
  sync_share_grid the mixed wait is recomputed from median_headway_minutes
  with the same formula as int_stop_wait_time (macros sync_share and
  wait_mixed); then, per stop, avg_exposed_wait_minutes is defined as in
  mart_stop_heat_wait (mean over hours with non-null wait of
  exposure_score * wait). Output: number of stops, median and p90 of it per
  risk_level. The metric is minutes of wait in direct sun, not a thermal
  stress index.
#}

with grid as (

    select cast(g as double) as sync_share_max
    from (values {% for g in var('sync_share_grid', [0, 0.25, 0.5, 0.6]) %}({{ g }}){% if not loop.last %}, {% endif %}{% endfor %}) as t(g)

),

hourly as (

    select h.osm_node_id, h.hour, h.exposure_score, h.risk_level, w.median_headway_minutes
    from {{ ref('mart_stop_heat_wait_hourly') }} h
    inner join {{ ref('int_stop_wait_time') }} w
        on h.gtfs_stop_id = w.gtfs_stop_id and h.hour = w.hour
    where w.median_headway_minutes is not null

),

per_stop as (

    select
        g.sync_share_max,
        h.osm_node_id,
        h.risk_level,
        avg(
            h.exposure_score
            * {{ wait_mixed(
                'h.median_headway_minutes',
                sync_share('h.median_headway_minutes', 'g.sync_share_max'),
                var('sync_wait_minutes', 2)) }}
        ) as avg_exposed_wait_minutes

    from hourly h
    cross join grid g
    group by 1, 2, 3

)

select
    sync_share_max,
    risk_level,
    count(*) as n_stops,
    median(avg_exposed_wait_minutes) as median_avg_exposed_wait_minutes,
    quantile_cont(avg_exposed_wait_minutes, 0.9) as p90_avg_exposed_wait_minutes

from per_stop
group by 1, 2
