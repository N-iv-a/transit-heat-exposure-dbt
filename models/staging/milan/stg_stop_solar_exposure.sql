{#
  Renaming stop_id -> osm_node_id here, not just at the mart layer: it's a
  different ID space from GTFS stop_id (see stg source docs), and a generic
  "stop_id" column name would invite an accidental join against the wait-time
  side further downstream.
#}

select
    stop_id as osm_node_id,
    cast(hour as integer) as hour,
    solar_azimuth,
    solar_elevation,
    in_building_shadow,
    has_shelter,
    exposed

from {{ source('raw_milan', 'stop_solar_exposure') }}
