{#
  The share of OSM shelter stops left 'unmatched' by int_osm_gtfs_stop_bridge
  must stay at or below var('max_unmatched_share', 0.12). Today it is about
  11.6% (340 of 2,931); a jump above the threshold usually means a broken
  ref join or a GTFS feed that lost stops, and would silently hollow out
  mart_stop_heat_wait. Returns one row only on violation.
#}

with shares as (

    select
        count(*) as total_stops,
        sum(case when match_method = 'unmatched' then 1 else 0 end) as unmatched_stops,
        sum(case when match_method = 'unmatched' then 1 else 0 end) * 1.0
            / nullif(count(*), 0) as unmatched_share
    from {{ ref('int_osm_gtfs_stop_bridge') }}

)

select total_stops, unmatched_stops, unmatched_share
from shares
where unmatched_share > {{ var('max_unmatched_share', 0.12) }}
