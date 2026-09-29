{#
  Valid municipal trees for the map's tree view (contract/map_data.md).
  shades_stop is exact: true if the tree is the tree recorded in
  stop_tree_shade (nearest tree casting the shadow) for at least one
  (stop, hour) -- so it is the nearest shading tree, not every tree whose
  crown would also cross the ray.
#}

select
    t.tree_id,
    t.genus,
    t.species,
    t.height_m,
    t.crown_diameter_m,
    t.lon,
    t.lat,
    s.tree_id is not null as shades_stop

from {{ ref('stg_milan_trees') }} t
left join (
    select distinct tree_id from {{ ref('stg_stop_tree_shade') }}
) s on t.tree_id = s.tree_id
where t.is_valid
