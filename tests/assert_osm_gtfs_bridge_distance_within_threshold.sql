{#
  int_osm_gtfs_stop_bridge's distance_m must be consistent with its
  match_method: 'ref' rows within 200 m, 'nearest' rows within 30 m, and
  'unmatched' rows entirely unmatched (gtfs_stop_id and distance_m both
  NULL). Fails if it returns any rows.
#}

select osm_node_id, gtfs_stop_id, match_method, distance_m
from {{ ref('int_osm_gtfs_stop_bridge') }}
where
    (match_method = 'ref' and (distance_m is null or distance_m > 200))
    or (match_method = 'nearest' and (distance_m is null or distance_m > 30))
    or (match_method = 'unmatched' and (gtfs_stop_id is not null or distance_m is not null))
