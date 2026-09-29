{#
  low <= mixed <= random <= high wherever the values are non-null
  (tolerance 0.01 min for the seed's 2-decimal rounding, 0.06 where
  wait_minutes_random is involved: median_wait_minutes is kept at 1 decimal). Fails if it
  returns any rows. See docs/MILAN_DATA_DECISIONS.md, section 7.
#}

select osm_node_id, hour, wait_minutes_low, wait_minutes, wait_minutes_random, wait_minutes_high
from {{ ref('mart_stop_heat_wait_hourly') }}
where
    (wait_minutes_low is not null and wait_minutes is not null
        and wait_minutes_low > wait_minutes + 0.01)
    or (wait_minutes is not null and wait_minutes_random is not null
        and wait_minutes > wait_minutes_random + 0.06)
    or (wait_minutes_random is not null and wait_minutes_high is not null
        and wait_minutes_random > wait_minutes_high + 0.06)
