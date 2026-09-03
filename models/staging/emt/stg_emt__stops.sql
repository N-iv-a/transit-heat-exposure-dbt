select
    'EMT-' || cast(stop_id as varchar) as stop_id,
    'EMT' as agency_code,
    stop_name,
    stop_lat,
    stop_lon,
    location_type,
    wheelchair_boarding

from {{ source('raw_emt', 'stops') }}
