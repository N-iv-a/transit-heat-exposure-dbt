{#
  Every OSM stop in stg_osm_shelter_stops must have exactly 7 rows (hours
  12-18) in mart_stop_heat_wait_hourly. Left join from the staging table so
  stops missing altogether (0 rows) are caught too. Fails if it returns
  any rows.
#}

select s.osm_node_id, count(h.osm_node_id) as n_rows
from {{ ref('stg_osm_shelter_stops') }} s
left join {{ ref('mart_stop_heat_wait_hourly') }} h
    on s.osm_node_id = h.osm_node_id
group by 1
having count(h.osm_node_id) <> 7
