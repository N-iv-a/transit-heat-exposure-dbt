{#
  n_departures >= 0 everywhere, and no (stop, hour) with a non-null wait and
  zero departures, in both int_stop_wait_time and mart_stop_heat_wait_hourly.
  Fails if it returns any rows.
#}

select 'int' as src, gtfs_stop_id as stop_key, hour
from {{ ref('int_stop_wait_time') }}
where n_departures < 0 or (wait_mixed_minutes is not null and n_departures = 0)

union all

select 'mart' as src, osm_node_id as stop_key, hour
from {{ ref('mart_stop_heat_wait_hourly') }}
where n_departures < 0 or (wait_minutes is not null and n_departures = 0)
