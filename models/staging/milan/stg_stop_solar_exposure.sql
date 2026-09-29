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
    in_tree_shadow,
    has_shelter,
    exposed,
    -- Hourly exposure weight: building shadow fully protects (0), tree crown
    -- shadow transmits {{ var('tree_transmissivity', 0.03) }} of the sun
    -- (Konarska et al. 2014, Theor. Appl. Climatol. 117, 363-376: 1.3-5.3%),
    -- a shelter
    -- attenuates but does not cancel exposure ({{ var('shelter_exposure_factor', 0.5) }},
    -- the project owner's call -- see docs/MILAN_DATA_DECISIONS.md), open sun
    -- counts fully (1). This is the only place shelter_exposure_factor and
    -- tree_transmissivity are read; downstream models consume the resulting exposure_score column.
    cast(
        case
            when in_building_shadow then 0
            when in_tree_shadow then {{ var('tree_transmissivity', 0.03) }}
            when has_shelter then {{ var('shelter_exposure_factor', 0.5) }}
            else 1
        end as double
    ) as exposure_score

from {{ source('raw_milan', 'stop_solar_exposure') }}
