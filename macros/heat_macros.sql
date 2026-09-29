{#
  Shared definitions, so that the main models and the sensitivity marts
  (T13) cannot drift apart.
#}

{# risk_level from a 0-7 exposure_score_hours: high >= 5, low <= 1, medium otherwise. #}
{% macro risk_level_from_score(score) %}
    case
        when {{ score }} >= 5 then 'high'
        when {{ score }} <= 1 then 'low'
        else 'medium'
    end
{% endmacro %}

{# Share of riders who time their arrival to the timetable (docs section 7.1). #}
{% macro sync_share(headway, share_max) %}
    case
        when {{ headway }} is null then null
        when {{ headway }} <= 5 then 0.0
        when {{ headway }} < 11 then {{ share_max }} * ({{ headway }} - 5) / 6.0
        else {{ share_max }}
    end
{% endmacro %}

{# Mixed wait: random riders wait H/2, synchronised ones least(H/2, sync_wait). #}
{% macro wait_mixed(headway, share, sync_wait) %}
    ((1 - {{ share }}) * {{ headway }} / 2.0
      + {{ share }} * least({{ headway }} / 2.0, {{ sync_wait }}))
{% endmacro %}
