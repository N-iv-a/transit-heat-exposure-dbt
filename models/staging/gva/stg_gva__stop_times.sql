select
    'GVA-' || cast(trip_id as varchar) as trip_id,
    'GVA-' || cast(stop_id as varchar) as stop_id,
    'GVA' as agency_code,
    stop_sequence,
    arrival_time,
    departure_time

from {{ source('raw_gva', 'stop_times') }}
