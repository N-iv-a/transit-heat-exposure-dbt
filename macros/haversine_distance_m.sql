{#
  Great-circle distance in metres between two lat/lon points, via the
  haversine formula. Earth radius taken as 6371000 m (mean radius) -- fine
  at the scale of a few hundred metres, the range this project uses it for.
#}

{% macro haversine_distance_m(lat1, lon1, lat2, lon2) %}
    (
        2 * 6371000 * asin(
            sqrt(
                pow(sin((radians({{ lat2 }}) - radians({{ lat1 }})) / 2), 2)
                + cos(radians({{ lat1 }})) * cos(radians({{ lat2 }}))
                * pow(sin((radians({{ lon2 }}) - radians({{ lon1 }})) / 2), 2)
            )
        )
    )
{% endmacro %}
