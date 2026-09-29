{#
  mart_stop_heat_risk.exposure_score_hours sums 7 hourly weights, each in
  [0, 1], so it must lie between 0 and 7. Fails if it returns any rows
  (including a NULL score).
#}

select osm_node_id, exposure_score_hours
from {{ ref('mart_stop_heat_risk') }}
where exposure_score_hours is null
    or exposure_score_hours < 0
    or exposure_score_hours > 7
