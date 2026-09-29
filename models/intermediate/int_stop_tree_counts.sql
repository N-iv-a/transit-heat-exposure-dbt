{#
  Valid municipal trees within 20 m (haversine) of each OSM stop. One row
  per stop (stops with no tree get 0). A lat/lon bounding box (20 m is
  ~0.00018 deg lat, ~0.00026 deg lon at Milan's latitude; box is a bit
  wider) prefilters the join, then the exact haversine distance decides.
#}

with stops as (

    select osm_node_id, lat, lon from {{ ref('stg_osm_shelter_stops') }}

),

trees as (

    select tree_id, lat, lon from {{ ref('stg_milan_trees') }} where is_valid

)

select
    s.osm_node_id,
    count(t.tree_id) as n_trees_20m

from stops s
left join trees t
    on t.lat between s.lat - 0.0003 and s.lat + 0.0003
    and t.lon between s.lon - 0.0004 and s.lon + 0.0004
    and {{ haversine_distance_m('s.lat', 's.lon', 't.lat', 't.lon') }} <= 20
group by s.osm_node_id
