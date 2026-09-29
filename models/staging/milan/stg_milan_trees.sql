{#
  Municipal tree census (ds2484). is_valid marks trees usable for the
  crown-shadow model: height 1-45 m, crown diameter 0.5-30 m, coordinates
  present. The same thresholds are constants in
  scripts/milan/solar_exposure.py (TREE_*); keep them in sync.
#}

select
    cast(tree_id as varchar) as tree_id,
    genus,
    species,
    height_m,
    crown_diameter_m,
    lon,
    lat,
    coalesce(
        height_m between 1 and 45
        and crown_diameter_m between 0.5 and 30
        and lon is not null
        and lat is not null,
        false
    ) as is_valid

from {{ source('raw_milan', 'trees') }}
