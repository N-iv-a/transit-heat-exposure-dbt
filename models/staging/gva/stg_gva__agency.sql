select
    'GVA-' || cast(agency_id as varchar) as agency_id,
    'GVA' as agency_code,
    agency_name,
    agency_url,
    agency_timezone

from {{ source('raw_gva', 'agency') }}
