-- MetricFlow time spine — required for cumulative + time-comparison metrics.
-- Reuses dim_calendar; just renames calendar_date to the canonical date_day.
SELECT
    calendar_date::DATE AS date_day
FROM {{ ref('dim_calendar') }}
