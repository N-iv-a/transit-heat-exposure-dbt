{#
  One row per trip occurrence: a trip_id on a specific service date.
  Grain: (agency_code, trip_id, service_date).
#}

select
    ite.agency_code,
    ite.trip_id,
    ite.route_id,
    ite.service_id,
    sd.date as service_date,
    ite.route_short_name,
    ite.route_type
from {{ ref('int_trips_enriched') }} as ite
inner join {{ ref('int_service_dates') }} as sd
    on ite.agency_code = sd.agency_code
    and ite.service_id = sd.service_id
