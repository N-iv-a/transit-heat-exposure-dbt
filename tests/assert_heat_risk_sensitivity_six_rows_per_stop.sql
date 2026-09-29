{# Each stop has exactly one row per factor in shelter_factor_grid (6 by default). Fails on any row returned. #}
select osm_node_id, count(*) as n_rows, count(distinct shelter_factor) as n_factors
from {{ ref('mart_stop_heat_risk_sensitivity') }}
group by 1
having count(*) <> {{ var('shelter_factor_grid', [0, 0.25, 0.5, 0.75, 1.0, 1.2]) | length }}
    or count(distinct shelter_factor) <> count(*)
