{#
  The value mart: how many trips pass by each stop, broken down by hour band
  and day type ("giorno tipo" — Monday, Saturday, Sunday, ...). This is the
  question a planner actually asks — "is this stop under-served on Sundays
  after 9pm?" — not just a list of stops.

  Grain: (agency_code, stop_id, day_type, arrival_hour). A trip's service
  can run on several day types (e.g. every weekday), so this join fans a
  stop_time row out once per day type before the count(*) — the aggregation
  step, not fct_stop_times itself, absorbs that fan-out.
#}

select
    fst.agency_code,
    fst.stop_id,
    isd.day_type,
    fst.arrival_hour,
    count(*) as trip_count
from {{ ref('fct_stop_times') }} as fst
inner join {{ ref('int_trips_enriched') }} as ite
    on fst.agency_code = ite.agency_code and fst.trip_id = ite.trip_id
inner join {{ ref('int_service_days') }} as isd
    on ite.agency_code = isd.agency_code and ite.service_id = isd.service_id
group by 1, 2, 3, 4
