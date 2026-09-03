select agency_id, agency_code, agency_name, agency_url, agency_timezone
from {{ ref('stg_emt__agency') }}

union all

select agency_id, agency_code, agency_name, agency_url, agency_timezone
from {{ ref('stg_gva__agency') }}
