{#
  tree_shade_hours (mart_stop_heat_risk and hourly mart) must be between 0
  and 7 (hours 13-19). Fails if it returns any rows.
#}

select osm_node_id, tree_shade_hours from {{ ref('mart_stop_heat_risk') }}
where tree_shade_hours is null or tree_shade_hours not between 0 and 7
union all
select osm_node_id, tree_shade_hours from {{ ref('mart_stop_heat_wait_hourly') }}
where tree_shade_hours is null or tree_shade_hours not between 0 and 7
