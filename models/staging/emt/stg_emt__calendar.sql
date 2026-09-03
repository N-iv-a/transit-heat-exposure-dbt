select
    'EMT-' || service_id as service_id,
    'EMT' as agency_code,
    cast(monday as boolean) as monday,
    cast(tuesday as boolean) as tuesday,
    cast(wednesday as boolean) as wednesday,
    cast(thursday as boolean) as thursday,
    cast(friday as boolean) as friday,
    cast(saturday as boolean) as saturday,
    cast(sunday as boolean) as sunday,
    strptime(cast(start_date as varchar), '%Y%m%d')::date as start_date,
    strptime(cast(end_date as varchar), '%Y%m%d')::date as end_date

from {{ source('raw_emt', 'calendar') }}
