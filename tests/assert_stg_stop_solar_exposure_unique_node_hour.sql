{#
  stg_stop_solar_exposure should have exactly one row per (osm_node_id,
  hour) — the source script computes exposure once per stop per hour.
  Fails if it returns any rows.
#}

select osm_node_id, hour, count(*) as n
from {{ ref('stg_stop_solar_exposure') }}
group by 1, 2
having count(*) > 1
