select
    'GVA-' || cast(trip_id as varchar) as trip_id,
    'GVA-' || cast(route_id as varchar) as route_id,
    'GVA-' || cast(service_id as varchar) as service_id,
    'GVA' as agency_code,
    cast(null as varchar) as trip_headsign,
    cast(shape_id as varchar) as shape_id

from {{ source('raw_gva', 'trips') }}
