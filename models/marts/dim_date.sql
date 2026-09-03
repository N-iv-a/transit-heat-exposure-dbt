{#
  Calendar spine covering the full range of service dates observed across
  both feeds (int_service_dates). Not joined by mart_service_frequency
  (that mart works at day-type grain to stay light — see README) but kept
  as a standard Kimball conformed dimension for any date-level analysis.
#}

with bounds as (
    select min(date) as min_date, max(date) as max_date
    from {{ ref('int_service_dates') }}
)

select
    gs.date::date as date,
    year(gs.date) as year,
    month(gs.date) as month,
    day(gs.date) as day,
    dayname(gs.date) as day_name,
    dayofweek(gs.date) in (0, 6) as is_weekend
from bounds, generate_series(bounds.min_date, bounds.max_date, interval 1 day) as gs(date)
