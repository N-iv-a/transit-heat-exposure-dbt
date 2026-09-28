{#
  One row per OSM stop node. ref is kept as-is (VARCHAR, not cast to
  integer): it's meant to mirror a GTFS stop_id, and GTFS stop_ids aren't
  always numeric (e.g. "ABBIATEGRASSO" in stop_wait_time.csv).
#}

select
    osm_node_id,
    ref,
    name,
    lat,
    lon

from {{ source('raw_milan', 'osm_shelter_stops') }}
