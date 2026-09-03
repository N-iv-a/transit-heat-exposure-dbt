select
    'EMT-' || trip_id as trip_id,
    'EMT-' || cast(stop_id as varchar) as stop_id,
    'EMT' as agency_code,
    stop_sequence,
    arrival_time,
    departure_time

from {{ source('raw_emt', 'stop_times') }}
