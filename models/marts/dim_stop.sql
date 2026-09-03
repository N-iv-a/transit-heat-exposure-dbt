select stop_id, agency_code, stop_name, stop_lat, stop_lon, location_type, wheelchair_boarding
from {{ ref('stg_emt__stops') }}

union all

select stop_id, agency_code, stop_name, stop_lat, stop_lon, location_type, wheelchair_boarding
from {{ ref('stg_gva__stops') }}
