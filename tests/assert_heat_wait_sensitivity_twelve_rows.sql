{# 4 sync_share_max values x 3 risk levels, each pair exactly once. Fails on any row returned. #}
with c as (
    select count(*) as n, count(distinct (sync_share_max, risk_level)) as n_distinct
    from {{ ref('mart_heat_wait_sensitivity') }}
)
select * from c
where n <> {{ var('sync_share_grid', [0, 0.25, 0.5, 0.6]) | length }} * 3
   or n_distinct <> n
