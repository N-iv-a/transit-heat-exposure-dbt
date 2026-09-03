{#
  Scheduled stop visits, at (trip_id, stop_sequence) grain — not expanded by
  calendar date, to keep this table's size proportional to the published
  schedule rather than the schedule times the number of service days.
  See mart_service_frequency for the day-type-level aggregation.

  arrival_hour is the raw GTFS hour (can exceed 23 for past-midnight trips,
  e.g. "25:30:00") normalized into a 0-23 band with a modulo — a handful of
  GVA rows go as high as 47, which reads as a source data-quality artifact
  rather than a genuine two-day-long bus trip.
#}

with stop_times as (

    select agency_code, trip_id, stop_id, stop_sequence, arrival_time, departure_time
    from {{ ref('stg_emt__stop_times') }}

    union all

    select agency_code, trip_id, stop_id, stop_sequence, arrival_time, departure_time
    from {{ ref('stg_gva__stop_times') }}

)

select
    st.agency_code,
    st.trip_id,
    ite.route_id,
    st.stop_id,
    st.stop_sequence,
    st.arrival_time,
    st.departure_time,
    cast(split_part(st.arrival_time, ':', 1) as integer) % 24 as arrival_hour
from stop_times as st
left join {{ ref('int_trips_enriched') }} as ite
    on st.agency_code = ite.agency_code and st.trip_id = ite.trip_id
