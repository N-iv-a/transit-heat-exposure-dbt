{#
  At the default sync_share_max the recomputed median must match the one
  from mart_stop_heat_wait (+-0.01). Only meaningful if the default is in
  the grid. Fails on any row returned.
#}
with ref_med as (
    select risk_level, median(avg_exposed_wait_minutes) as med
    from {{ ref('mart_stop_heat_wait') }}
    where avg_exposed_wait_minutes is not null
    group by 1
)
select s.risk_level, s.median_avg_exposed_wait_minutes, r.med
from {{ ref('mart_heat_wait_sensitivity') }} s
join ref_med r using (risk_level)
where s.sync_share_max = {{ var('sync_share_max', 0.5) }}
  and abs(s.median_avg_exposed_wait_minutes - r.med) > 0.01
