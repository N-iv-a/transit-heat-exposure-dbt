select
    'GVA-' || cast(route_id as varchar) as route_id,
    'GVA-' || cast(agency_id as varchar) as agency_id,
    'GVA' as agency_code,
    route_short_name,
    route_long_name,
    route_type

from {{ source('raw_gva', 'routes') }}
