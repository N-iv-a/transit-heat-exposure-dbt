select
    'EMT-' || cast(route_id as varchar) as route_id,
    'EMT-' || agency_id as agency_id,
    'EMT' as agency_code,
    route_short_name,
    route_long_name,
    route_type

from {{ source('raw_emt', 'routes') }}
