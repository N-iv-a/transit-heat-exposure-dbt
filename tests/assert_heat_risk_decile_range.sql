{# exposure_decile must span exactly 1..10 (stops > 10). Fails on any row returned. #}
select min(exposure_decile) as lo, max(exposure_decile) as hi
from {{ ref('mart_stop_heat_risk') }}
having min(exposure_decile) <> 1 or max(exposure_decile) <> 10
