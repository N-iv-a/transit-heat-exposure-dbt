{#
  One row per trip, enriched with its route and agency attributes.
  Calendar/service-day expansion is intentionally kept separate
  (int_service_dates, int_service_days) so this model stays at trip grain.
#}

with emt_trips as (

    select
        t.agency_code,
        t.trip_id,
        t.route_id,
        t.service_id,
        t.trip_headsign,
        r.route_short_name,
        r.route_long_name,
        r.route_type,
        a.agency_name
    from {{ ref('stg_emt__trips') }} as t
    left join {{ ref('stg_emt__routes') }} as r on t.route_id = r.route_id
    left join {{ ref('stg_emt__agency') }} as a on r.agency_id = a.agency_id

),

gva_trips as (

    select
        t.agency_code,
        t.trip_id,
        t.route_id,
        t.service_id,
        t.trip_headsign,
        r.route_short_name,
        r.route_long_name,
        r.route_type,
        a.agency_name
    from {{ ref('stg_gva__trips') }} as t
    left join {{ ref('stg_gva__routes') }} as r on t.route_id = r.route_id
    left join {{ ref('stg_gva__agency') }} as a on r.agency_id = a.agency_id

)

select * from emt_trips
union all
select * from gva_trips
