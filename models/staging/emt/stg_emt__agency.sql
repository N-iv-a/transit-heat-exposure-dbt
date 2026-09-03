select
    'EMT-' || agency_id as agency_id,
    'EMT' as agency_code,
    agency_name,
    agency_url,
    agency_timezone

from {{ source('raw_emt', 'agency') }}
