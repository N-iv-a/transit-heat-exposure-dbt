select
    'EMT-' || service_id as service_id,
    'EMT' as agency_code,
    strptime(cast(date as varchar), '%Y%m%d')::date as date,
    exception_type

from {{ source('raw_emt', 'calendar_dates') }}
