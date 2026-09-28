{#
  mart_stop_heat_wait.avg_exposed_wait_minutes must equal the average of
  exposed_wait_minutes recomputed from mart_stop_heat_wait_hourly for the
  same osm_node_id (ignoring NULL hours), within 1e-9, and must be NULL
  exactly when the recomputed average is NULL (no hour with wait data).
  Fails if it returns any rows.
#}

with recomputed as (

    select osm_node_id, avg(exposed_wait_minutes) as recomputed_avg
    from {{ ref('mart_stop_heat_wait_hourly') }}
    group by 1

)

select
    w.osm_node_id,
    w.avg_exposed_wait_minutes,
    r.recomputed_avg

from {{ ref('mart_stop_heat_wait') }} w
left join recomputed r on w.osm_node_id = r.osm_node_id
where
    (w.avg_exposed_wait_minutes is null) != (r.recomputed_avg is null)
    or (
        w.avg_exposed_wait_minutes is not null
        and r.recomputed_avg is not null
        and abs(w.avg_exposed_wait_minutes - r.recomputed_avg) > 1e-9
    )
