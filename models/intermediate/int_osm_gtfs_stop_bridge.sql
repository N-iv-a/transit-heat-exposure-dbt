{#
  Bridge between the two stop-id spaces used in this project: OSM node ids
  (stg_osm_shelter_stops, from the Overpass shelter export) and GTFS
  stop_ids (int_stop_wait_time). Grain: one row per osm_node_id (2,931
  rows) -- match_method explains how (or whether) each one was matched to
  a GTFS stop:

    - 'ref': the OSM ref tag equals a GTFS stop_id, and the two points are
      within 200 m of each other (a sanity check on the OSM ref tag, not a
      matching criterion in itself -- refs that fail it fall through to
      'nearest'/'unmatched' below).
    - 'nearest': no usable ref match, but there's a GTFS stop within 30 m;
      the closest one wins (ties broken by gtfs_stop_id).
    - 'unmatched': neither of the above -- gtfs_stop_id and distance_m are
      both NULL.

  Distances are haversine, in metres (macros/haversine_distance_m.sql).

  Downstream note: this bridge only connects the *stop* dimension. The two
  sides it joins still come from different reference days -- solar
  exposure is for 2026-06-28 (the hottest day found in the ARPA analysis),
  wait time is for 2026-09-13 (see docs/MILAN_DATA_DECISIONS.md) -- so
  anything built on top of this bridge (e.g. mart_stop_heat_wait) is
  combining a summer-heat day with an unrelated autumn service day, not
  measuring wait time under the exact conditions of the exposure day.
#}

with osm_stops as (

    select osm_node_id, ref, name, lat, lon
    from {{ ref('stg_osm_shelter_stops') }}

),

gtfs_stops as (

    select distinct gtfs_stop_id, stop_name, lat, lon
    from {{ ref('int_stop_wait_time') }}

),

ref_candidates as (

    select
        o.osm_node_id,
        g.gtfs_stop_id,
        {{ haversine_distance_m('o.lat', 'o.lon', 'g.lat', 'g.lon') }} as distance_m

    from osm_stops o
    inner join gtfs_stops g
        on o.ref = g.gtfs_stop_id

),

ref_matches as (

    select osm_node_id, gtfs_stop_id, distance_m
    from ref_candidates
    where distance_m <= 200

),

nearest_candidates as (

    select
        o.osm_node_id,
        g.gtfs_stop_id,
        {{ haversine_distance_m('o.lat', 'o.lon', 'g.lat', 'g.lon') }} as distance_m,
        row_number() over (
            partition by o.osm_node_id
            order by {{ haversine_distance_m('o.lat', 'o.lon', 'g.lat', 'g.lon') }}, g.gtfs_stop_id
        ) as rn

    from osm_stops o
    inner join gtfs_stops g
        on {{ haversine_distance_m('o.lat', 'o.lon', 'g.lat', 'g.lon') }} <= 30
    where o.osm_node_id not in (select osm_node_id from ref_matches)

),

nearest_matches as (

    select osm_node_id, gtfs_stop_id, distance_m
    from nearest_candidates
    where rn = 1

)

select
    o.osm_node_id,
    coalesce(rm.gtfs_stop_id, nm.gtfs_stop_id) as gtfs_stop_id,
    case
        when rm.gtfs_stop_id is not null then 'ref'
        when nm.gtfs_stop_id is not null then 'nearest'
        else 'unmatched'
    end as match_method,
    coalesce(rm.distance_m, nm.distance_m) as distance_m

from osm_stops o
left join ref_matches rm on o.osm_node_id = rm.osm_node_id
left join nearest_matches nm on o.osm_node_id = nm.osm_node_id
