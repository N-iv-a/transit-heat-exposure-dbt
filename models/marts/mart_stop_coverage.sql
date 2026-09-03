{#
  Per stop: how many distinct routes serve it, and its scheduled service
  span. A quick way to spot stops served by a single route (single point of
  failure) versus well-connected hubs.
#}

select
    ds.stop_id,
    ds.agency_code,
    ds.stop_name,
    count(distinct fst.route_id) as route_count,
    min(fst.arrival_time) as first_scheduled_arrival,
    max(fst.arrival_time) as last_scheduled_arrival
from {{ ref('dim_stop') }} as ds
left join {{ ref('fct_stop_times') }} as fst
    on ds.stop_id = fst.stop_id and ds.agency_code = fst.agency_code
group by 1, 2, 3
