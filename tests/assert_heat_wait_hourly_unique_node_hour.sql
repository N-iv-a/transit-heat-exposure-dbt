{#
  mart_stop_heat_wait_hourly should have exactly one row per (osm_node_id,
  hour) -- see contract/map_data.md. Fails if it returns any rows.
#}

select osm_node_id, hour, count(*) as n
from {{ ref('mart_stop_heat_wait_hourly') }}
group by 1, 2
having count(*) > 1
