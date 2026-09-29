{#
  sync_share must lie in [0, sync_share_max] (var, default 0.5).
  Fails if it returns any rows.
#}

select gtfs_stop_id, hour, sync_share
from {{ ref('int_stop_wait_time') }}
where sync_share < 0 or sync_share > {{ var('sync_share_max', 0.5) }} + 1e-9
