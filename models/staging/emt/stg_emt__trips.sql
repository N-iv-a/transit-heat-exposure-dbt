select
    'EMT-' || trip_id as trip_id,
    'EMT-' || cast(route_id as varchar) as route_id,
    'EMT-' || service_id as service_id,
    'EMT' as agency_code,
    trip_headsign,
    shape_id

from {{ source('raw_emt', 'trips') }}
