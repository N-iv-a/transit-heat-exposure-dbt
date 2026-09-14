{#
  Grain change from stg_stop_solar_exposure (stop x hour) to stop: for each
  of the 2,931 OSM stops, how many of the 7 critical hours (12:00-18:00,
  June 28 2026 -- the hottest day found in the ARPA analysis) is it exposed
  (no building shadow, no shelter) for.

  risk_level flags the 724 stops (25%) exposed at every single hour --
  never shadowed, never sheltered -- as the actionable finding from
  docs/MILAN_DATA_DECISIONS.md section 6: candidates for shelter/shade
  investment, as opposed to stops exposed only part of the window.

  Deliberately does not bring in int_stop_wait_time: that model keys off
  GTFS stop_id, this one off OSM node id, and no join between the two ID
  spaces is attempted anywhere in this project (see
  docs/MILAN_DATA_DECISIONS.md, section 7, and int_stop_wait_time.sql).
  Heat risk (this mart) and wait time (int_stop_wait_time) stay two
  separate signals, read as two separate maps, not one combined score.
#}

select
    osm_node_id,
    count(*) as hours_measured,
    sum(case when exposed then 1 else 0 end) as hours_exposed,
    round(sum(case when exposed then 1 else 0 end) * 1.0 / count(*), 3) as pct_hours_exposed,
    max(case when has_shelter then 1 else 0 end) = 1 as has_shelter,
    case
        when sum(case when exposed then 1 else 0 end) = count(*) then 'high'
        when sum(case when exposed then 1 else 0 end) = 0 then 'low'
        else 'medium'
    end as risk_level

from {{ ref('stg_stop_solar_exposure') }}
group by 1
