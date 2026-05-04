-- NCUA 5300 call report — one row per (period_end_quarter × line_code).
--
-- Aggregates dim_loan + dim_deposit_product + downstream marts onto the
-- line-item catalog (cecl_segments + ncua_5300_lines seeds). For every
-- quarter end across the history window we emit:
--   * Schedule CB (loans + shares totals by product class)
--   * Schedule CL (allowance roll-forward summary)
--   * Schedule RC (assets + net worth)
--
-- The audit harness (HUG-166) will cross-foot Schedule CB totals against
-- dim_loan / deposit_accounts within $1.

WITH calendar_quarters AS (
    SELECT DISTINCT
        DATE_TRUNC('quarter', month_start_date)::DATE
            + INTERVAL '3 months' - INTERVAL '1 day' AS period_end_quarter
    FROM {{ ref('dim_calendar') }}
    WHERE is_month_end = TRUE
      AND month_num IN (3, 6, 9, 12)
),

loan_balances_by_quarter AS (
    SELECT
        DATE_TRUNC('quarter', perf.snapshot_date)::DATE
            + INTERVAL '3 months' - INTERVAL '1 day' AS period_end_quarter,
        dim.ncua_5300_line_code,
        SUM(perf.balance) AS line_value
    FROM {{ ref('fct_loan_performance') }} perf
    INNER JOIN {{ ref('dim_loan') }} dim USING (loan_id)
    WHERE dim.status != 'paid_off'
      AND perf.snapshot_date IN (
          SELECT month_start_date FROM {{ ref('dim_calendar') }}
          WHERE month_num IN (3, 6, 9, 12) AND is_month_end = FALSE
      )
    GROUP BY 1, 2
),

deposit_balances_by_quarter AS (
    SELECT
        DATE_TRUNC('quarter', dm.as_of_month)::DATE
            + INTERVAL '3 months' - INTERVAL '1 day' AS period_end_quarter,
        dp.ncua_5300_line_code,
        SUM(dm.total_balance) AS line_value
    FROM {{ ref('fct_deposits_monthly') }} dm
    INNER JOIN {{ ref('dim_deposit_product') }} dp USING (deposit_product_id)
    WHERE EXTRACT(MONTH FROM dm.as_of_month) IN (3, 6, 9, 12)
    GROUP BY 1, 2
),

total_loans AS (
    SELECT
        period_end_quarter,
        '386' AS ncua_5300_line_code,
        SUM(line_value) AS line_value
    FROM loan_balances_by_quarter
    GROUP BY 1
),

delinq_60_plus AS (
    SELECT
        DATE_TRUNC('quarter', perf.snapshot_date)::DATE
            + INTERVAL '3 months' - INTERVAL '1 day' AS period_end_quarter,
        '541' AS ncua_5300_line_code,
        SUM(perf.balance) AS line_value
    FROM {{ ref('fct_loan_performance') }} perf
    WHERE perf.days_past_due >= 60
      AND EXTRACT(MONTH FROM perf.snapshot_date) IN (3, 6, 9, 12)
    GROUP BY 1
),

total_shares AS (
    SELECT
        period_end_quarter,
        '018' AS ncua_5300_line_code,
        SUM(line_value) AS line_value
    FROM deposit_balances_by_quarter
    GROUP BY 1
),

assets_and_net_worth AS (
    -- Synthetic: total assets ≈ total loans / 0.65 (industry norm); net worth
    -- ≈ 9.5% of assets. Lets the analyst reconcile but reflects synthetic data.
    SELECT
        period_end_quarter,
        unnest(ARRAY['010', '997', '997a']::TEXT[]) AS ncua_5300_line_code,
        unnest(ARRAY[
            line_value / 0.65,
            line_value / 0.65 * 0.095,
            0.095
        ]::NUMERIC[]) AS line_value
    FROM total_loans
),

cecl_lines AS (
    SELECT
        period_end_quarter,
        ncua_5300_line_code,
        SUM(line_value) AS line_value
    FROM (
        SELECT
            DATE_TRUNC('quarter', period_end_month)::DATE
                + INTERVAL '3 months' - INTERVAL '1 day' AS period_end_quarter,
            '550' AS ncua_5300_line_code,
            beginning_balance AS line_value
        FROM {{ ref('fct_cecl_allowance_rollforward') }}
        WHERE EXTRACT(MONTH FROM period_end_month) IN (3, 6, 9, 12)
        UNION ALL
        SELECT
            DATE_TRUNC('quarter', period_end_month)::DATE
                + INTERVAL '3 months' - INTERVAL '1 day',
            '550c', ending_balance
        FROM {{ ref('fct_cecl_allowance_rollforward') }}
        WHERE EXTRACT(MONTH FROM period_end_month) IN (3, 6, 9, 12)
        UNION ALL
        SELECT
            DATE_TRUNC('quarter', period_end_month)::DATE
                + INTERVAL '3 months' - INTERVAL '1 day',
            '551', provision_expense
        FROM {{ ref('fct_cecl_allowance_rollforward') }}
        WHERE EXTRACT(MONTH FROM period_end_month) IN (3, 6, 9, 12)
        UNION ALL
        SELECT
            DATE_TRUNC('quarter', period_end_month)::DATE
                + INTERVAL '3 months' - INTERVAL '1 day',
            '550a', recoveries
        FROM {{ ref('fct_cecl_allowance_rollforward') }}
        WHERE EXTRACT(MONTH FROM period_end_month) IN (3, 6, 9, 12)
        UNION ALL
        SELECT
            DATE_TRUNC('quarter', period_end_month)::DATE
                + INTERVAL '3 months' - INTERVAL '1 day',
            '550b', charge_offs
        FROM {{ ref('fct_cecl_allowance_rollforward') }}
        WHERE EXTRACT(MONTH FROM period_end_month) IN (3, 6, 9, 12)
    ) sub
    GROUP BY 1, 2
),

all_lines AS (
    SELECT * FROM loan_balances_by_quarter
    UNION ALL SELECT * FROM deposit_balances_by_quarter
    UNION ALL SELECT * FROM total_loans
    UNION ALL SELECT * FROM total_shares
    UNION ALL SELECT * FROM delinq_60_plus
    UNION ALL SELECT * FROM assets_and_net_worth
    UNION ALL SELECT * FROM cecl_lines
)

SELECT
    al.period_end_quarter,
    al.ncua_5300_line_code,
    cat.schedule,
    cat.label,
    al.line_value
FROM all_lines al
INNER JOIN calendar_quarters USING (period_end_quarter)
INNER JOIN {{ ref('ncua_5300_lines') }} cat
    ON cat.line_code = al.ncua_5300_line_code
WHERE al.ncua_5300_line_code IS NOT NULL
