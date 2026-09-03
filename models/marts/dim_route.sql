select route_id, agency_id, agency_code, route_short_name, route_long_name, route_type
from {{ ref('stg_emt__routes') }}

union all

select route_id, agency_id, agency_code, route_short_name, route_long_name, route_type
from {{ ref('stg_gva__routes') }}
