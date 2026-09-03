{#
  Which weekday "type" each service actually runs on, derived from the exact
  calendar dates in int_service_dates rather than maintained separately —
  one definition of a service's calendar, not two.

  Note for GVA: the feed only covers a ~2 week rolling window, so this
  reflects the days observed in that window, not a long-run weekly pattern.
#}

select distinct
    agency_code,
    service_id,
    dayname(date) as day_type,
    dayofweek(date) in (0, 6) as is_weekend
from {{ ref('int_service_dates') }}
