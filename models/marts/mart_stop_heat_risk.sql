{#
  Grain change from stg_stop_solar_exposure (stop x hour) to stop: for each
  of the 2,931 OSM stops, how exposed it is over the 7 critical hours
  (13:00-19:00 CEST, June 28 2026 -- the hottest day found in the ARPA analysis).

  Two readings of exposure, side by side:

  - Weighted (exposure_score_hours / pct_exposure_score / risk_level): sums
    stg_stop_solar_exposure.exposure_score, which treats a shelter as an
    attenuating factor rather than full protection -- a shelter's shade is
    real but does not read as equivalent to a building's shadow (the
    project owner's call, see docs/MILAN_DATA_DECISIONS.md section 6).
    risk_level buckets the resulting 0-7 score: high >= 5, low <= 1,
    medium otherwise.
  - Binary (hours_exposed_binary / pct_hours_exposed_binary /
    risk_level_binary): the original all-or-nothing exposed flag (shelter
    counts the same as no protection at all). risk_level_binary keeps the
    724 stops (25%) exposed at every single hour -- never shadowed, never
    sheltered -- readable exactly as before, as the actionable finding from
    docs/MILAN_DATA_DECISIONS.md section 6: candidates for shelter/shade
    investment, as opposed to stops exposed only part of the window.

  Deliberately does not bring in int_stop_wait_time: that model keys off
  GTFS stop_id, this one off OSM node id. A bridge between the two ID
  spaces now exists (int_osm_gtfs_stop_bridge.sql, used by
  mart_stop_heat_wait.sql), but this mart is kept as-is by choice: heat
  risk (this mart) and wait time (int_stop_wait_time) stay two separate
  signals, read as two separate maps, not one combined score.
#}

select
    e.osm_node_id,
    count(*) as hours_measured,
    round(sum(exposure_score), 3) as exposure_score_hours,
    round(sum(exposure_score) / count(*), 3) as pct_exposure_score,
    sum(case when exposed then 1 else 0 end) as hours_exposed_binary,
    round(sum(case when exposed then 1 else 0 end) * 1.0 / count(*), 3) as pct_hours_exposed_binary,
    max(case when has_shelter then 1 else 0 end) = 1 as has_shelter,
    {{ risk_level_from_score('sum(exposure_score)') }} as risk_level,
    case
        when sum(case when exposed then 1 else 0 end) = count(*) then 'high'
        when sum(case when exposed then 1 else 0 end) = 0 then 'low'
        else 'medium'
    end as risk_level_binary,
    -- T13: decile of exposure_score_hours across stops, 10 = most exposed
    ntile(10) over (order by sum(exposure_score)) as exposure_decile,
    -- T13: true if risk_level is identical for every shelter factor in the grid
    max(st.n_levels) = 1 as risk_level_stable,
    -- T15: hours (13-19) in tree crown shadow, and valid trees within 20 m
    sum(case when e.in_tree_shadow then 1 else 0 end) as tree_shade_hours,
    max(tc.n_trees_20m) as n_trees_20m

from {{ ref('stg_stop_solar_exposure') }} e
left join (
    select osm_node_id, count(distinct risk_level) as n_levels
    from {{ ref('mart_stop_heat_risk_sensitivity') }}
    group by 1
) st on e.osm_node_id = st.osm_node_id
left join {{ ref('int_stop_tree_counts') }} tc on e.osm_node_id = tc.osm_node_id
group by e.osm_node_id
