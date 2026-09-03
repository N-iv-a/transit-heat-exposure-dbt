select
    'GVA-' || cast(service_id as varchar) as service_id,
    'GVA' as agency_code,
    strptime(cast(date as varchar), '%Y%m%d')::date as date,
    exception_type

from {{ source('raw_gva', 'calendar_dates') }}
