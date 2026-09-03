{#
  fct_trips should have exactly one row per (agency_code, trip_id,
  service_date) — a trip cannot occur twice on the same date. Fails if it
  returns any rows.
#}

select agency_code, trip_id, service_date, count(*) as n
from {{ ref('fct_trips') }}
group by 1, 2, 3
having count(*) > 1
