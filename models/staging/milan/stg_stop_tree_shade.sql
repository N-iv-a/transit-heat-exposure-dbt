select
    stop_id as osm_node_id,
    cast(hour as integer) as hour,
    cast(tree_id as varchar) as tree_id

from {{ source('raw_milan', 'stop_tree_shade') }}
