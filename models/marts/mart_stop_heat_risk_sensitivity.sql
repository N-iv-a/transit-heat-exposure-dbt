{#
  Sensitivity of risk_level to the shelter factor (T13). Grain: one row per
  (osm_node_id, shelter_factor) = 2,931 stops x 6 factors. The factor is the
  exposure weight of a stop in sun WITH a shelter: 0 = shelter protects
  fully, 1 = no protection, > 1 = closed shelter that worsens heat stress
  (Lanza et al. 2025). Values in var shelter_factor_grid.

  exposure_score_hours = sum over the 7 hours of: 0 in building shadow,
  tree_transmissivity in tree shadow, factor in sun with shelter, 1 in sun without shelter. Same definition as
  stg_stop_solar_exposure, but with the factor varied. risk_level uses the
  same thresholds as mart_stop_heat_risk (macro risk_level_from_score).
#}

with factors as (

    select cast(f as double) as shelter_factor
    from (values {% for f in var('shelter_factor_grid', [0, 0.25, 0.5, 0.75, 1.0, 1.2]) %}({{ f }}){% if not loop.last %}, {% endif %}{% endfor %}) as t(f)

),

hourly as (

    select osm_node_id, in_building_shadow, in_tree_shadow, has_shelter
    from {{ ref('stg_stop_solar_exposure') }}

),

scored as (

    select
        h.osm_node_id,
        f.shelter_factor,
        round(sum(
            case
                when h.in_building_shadow then 0.0
                when h.in_tree_shadow then {{ var('tree_transmissivity', 0.03) }}
                when h.has_shelter then f.shelter_factor
                else 1.0
            end
        ), 6) as exposure_score_hours

    from hourly h
    cross join factors f
    group by 1, 2

)

select
    osm_node_id,
    shelter_factor,
    exposure_score_hours,
    {{ risk_level_from_score('exposure_score_hours') }} as risk_level

from scored
