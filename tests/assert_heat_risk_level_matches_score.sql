{#
  mart_stop_heat_risk.risk_level must agree with exposure_score_hours:
  high when >= 5, low when <= 1, medium otherwise. Guards against the
  buckets and the score drifting apart. Fails if it returns any rows.
#}

select
    osm_node_id,
    exposure_score_hours,
    risk_level,
    case
        when exposure_score_hours >= 5 then 'high'
        when exposure_score_hours <= 1 then 'low'
        else 'medium'
    end as expected_risk_level
from {{ ref('mart_stop_heat_risk') }}
where risk_level is distinct from case
        when exposure_score_hours >= 5 then 'high'
        when exposure_score_hours <= 1 then 'low'
        else 'medium'
    end
