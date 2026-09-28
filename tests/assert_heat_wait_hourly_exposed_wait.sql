{#
  exposed_wait_minutes must equal exposure_score * wait_minutes (within
  1e-9), and must be NULL exactly when wait_minutes is NULL -- see
  contract/map_data.md. Fails if it returns any rows.
#}

select osm_node_id, hour, exposure_score, wait_minutes, exposed_wait_minutes
from {{ ref('mart_stop_heat_wait_hourly') }}
where
    (wait_minutes is null and exposed_wait_minutes is not null)
    or (
        wait_minutes is not null
        and (
            exposed_wait_minutes is null
            or abs(exposed_wait_minutes - exposure_score * wait_minutes) > 1e-9
        )
    )
