WITH dates AS (
    SELECT generate_series(
        '2022-07-01'::DATE,
        '2025-06-30'::DATE,
        '1 day'::INTERVAL
    )::DATE AS calendar_date
)
SELECT
    calendar_date,
    DATE_TRUNC('month', calendar_date)::DATE                          AS month_start_date,
    (DATE_TRUNC('month', calendar_date + INTERVAL '1 month')
        - INTERVAL '1 day')::DATE                                     AS month_end_date,
    EXTRACT(YEAR    FROM calendar_date)::INT                          AS year,
    EXTRACT(MONTH   FROM calendar_date)::INT                          AS month_num,
    EXTRACT(QUARTER FROM calendar_date)::INT                          AS quarter,
    CASE
        WHEN EXTRACT(MONTH FROM calendar_date) >= 7
        THEN EXTRACT(YEAR FROM calendar_date)::INT + 1
        ELSE EXTRACT(YEAR FROM calendar_date)::INT
    END                                                               AS fiscal_year,
    (calendar_date = (DATE_TRUNC('month', calendar_date + INTERVAL '1 month')
        - INTERVAL '1 day')::DATE)                                    AS is_month_end
FROM dates
