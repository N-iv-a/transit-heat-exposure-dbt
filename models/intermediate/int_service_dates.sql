{#
  One row per (agency_code, service_id, date) that a service actually runs.

  EMT ships a full calendar.txt (weekday pattern + date range) plus
  calendar_dates.txt exceptions (add/remove single days) — the classic GTFS
  combination, expanded here.

  GVA ships no calendar.txt at all: calendar_dates.txt (exception_type = 1
  only) *is* the calendar, and it only covers a rolling ~2 week window. So
  for GVA this model is just a pass-through of the "added" rows.
#}

with emt_calendar_expanded as (

    select
        c.service_id,
        gs.date::date as date
    from {{ ref('stg_emt__calendar') }} as c,
        generate_series(c.start_date, c.end_date, interval 1 day) as gs(date)
    where
        (dayofweek(gs.date) = 0 and c.sunday)
        or (dayofweek(gs.date) = 1 and c.monday)
        or (dayofweek(gs.date) = 2 and c.tuesday)
        or (dayofweek(gs.date) = 3 and c.wednesday)
        or (dayofweek(gs.date) = 4 and c.thursday)
        or (dayofweek(gs.date) = 5 and c.friday)
        or (dayofweek(gs.date) = 6 and c.saturday)

),

emt_removed as (
    select service_id, date
    from {{ ref('stg_emt__calendar_dates') }}
    where exception_type = 2
),

emt_added as (
    select service_id, date
    from {{ ref('stg_emt__calendar_dates') }}
    where exception_type = 1
),

emt_service_dates as (
    (
        select service_id, date from emt_calendar_expanded
        except
        select service_id, date from emt_removed
    )
    union
    select service_id, date from emt_added
),

gva_service_dates as (
    select service_id, date
    from {{ ref('stg_gva__calendar_dates') }}
    where exception_type = 1
)

select 'EMT' as agency_code, service_id, date from emt_service_dates
union all
select 'GVA' as agency_code, service_id, date from gva_service_dates
