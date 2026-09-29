{#
  in_tree_shadow is defined only for stops not already in building shadow:
  no (stop, hour) may have both. Fails if it returns any rows.
#}

select osm_node_id, hour
from {{ ref('stg_stop_solar_exposure') }}
where in_building_shadow and in_tree_shadow
