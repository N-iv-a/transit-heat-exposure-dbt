select
    'GVA-' || cast(stop_id as varchar) as stop_id,
    'GVA' as agency_code,
    stop_name,
    stop_lat,
    stop_lon,
    cast(null as bigint) as location_type,
    cast(null as bigint) as wheelchair_boarding

from {{ source('raw_gva', 'stops') }}
