{#
  Custom test (doc requirement): arrival_time must never be later than
  departure_time at the same stop. Fails if it returns any rows.
#}

select agency_code, trip_id, stop_id, stop_sequence, arrival_time, departure_time
from {{ ref('fct_stop_times') }}
where arrival_time > departure_time
