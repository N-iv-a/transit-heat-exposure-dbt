{#
  stg_stop_solar_exposure.exposure_score must be one of the three allowed
  hourly weights -- 0 (building shadow), var('tree_transmissivity', 0.03)
  (tree crown shadow), var('shelter_exposure_factor', 0.5) (shelter, no building shadow), or 1 (fully open) -- and must be 0
  whenever in_building_shadow is true. Fails if it returns any rows.
#}

select osm_node_id, hour, in_building_shadow, has_shelter, exposure_score
from {{ ref('stg_stop_solar_exposure') }}
where
    exposure_score not in (0, {{ var('tree_transmissivity', 0.03) }}, {{ var('shelter_exposure_factor', 0.5) }}, 1)
    or (in_building_shadow and exposure_score <> 0)
    or (in_tree_shadow and not in_building_shadow and exposure_score <> {{ var('tree_transmissivity', 0.03) }})
