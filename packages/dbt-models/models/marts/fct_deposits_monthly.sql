WITH calendar_months AS (
    SELECT DISTINCT
        month_start_date  AS as_of_month,
        fiscal_year
    FROM {{ ref('dim_calendar') }}
    WHERE month_start_date <= DATE_TRUNC('month', CURRENT_DATE)
),

active_accounts AS (
    SELECT
        cm.as_of_month,
        cm.fiscal_year,
        a.account_id,
        a.branch_id,
        a.deposit_product_id::TEXT                                        AS deposit_product_id,
        a.current_balance::NUMERIC                                    AS balance,
        DATE_TRUNC('month', a.opened_at)::DATE                       AS opened_month,
        DATE_TRUNC('month', a.closed_at)::DATE                       AS closed_month
    FROM deposit_accounts a
    CROSS JOIN calendar_months cm
    WHERE cm.as_of_month >= DATE_TRUNC('month', a.opened_at)
      AND (a.closed_at IS NULL
           OR cm.as_of_month <= DATE_TRUNC('month', a.closed_at))
),

grain AS (
    SELECT
        as_of_month,
        deposit_product_id,
        branch_id,
        fiscal_year,
        COUNT(DISTINCT account_id)                                    AS account_count,
        SUM(balance)                                                  AS total_balance,
        SUM(balance) / NULLIF(COUNT(DISTINCT account_id), 0)         AS avg_balance_per_customer,
        COUNT(DISTINCT CASE WHEN opened_month = as_of_month
                            THEN account_id END)                     AS opened_count,
        COUNT(DISTINCT CASE WHEN closed_month = as_of_month
                            THEN account_id END)                     AS closed_count
    FROM active_accounts
    GROUP BY as_of_month, deposit_product_id, branch_id, fiscal_year
),

with_changes AS (
    SELECT
        *,
        total_balance - LAG(total_balance, 1, total_balance) OVER (
            PARTITION BY deposit_product_id, branch_id
            ORDER BY as_of_month
        )                                                             AS mtd_change,
        total_balance - FIRST_VALUE(total_balance) OVER (
            PARTITION BY deposit_product_id, branch_id, fiscal_year
            ORDER BY as_of_month
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        )                                                             AS ytd_change
    FROM grain
)

SELECT
    c.as_of_month::DATE                                               AS as_of_month,
    c.deposit_product_id::TEXT                                        AS deposit_product_id,
    c.branch_id::INT                                                  AS branch_id,
    c.account_count::INT                                              AS account_count,
    c.total_balance::NUMERIC                                          AS total_balance,
    c.avg_balance_per_customer::NUMERIC                               AS avg_balance_per_customer,
    c.opened_count::INT                                               AS opened_count,
    c.closed_count::INT                                               AS closed_count,
    c.mtd_change::NUMERIC                                             AS mtd_change,
    c.ytd_change::NUMERIC                                             AS ytd_change,
    dp.is_core_deposit::BOOLEAN                                       AS is_core_deposit,
    (c.as_of_month::TEXT
        || '|' || c.deposit_product_id
        || '|' || c.branch_id::TEXT)::TEXT                           AS row_id
FROM with_changes c
INNER JOIN {{ ref('dim_deposit_product') }} dp
        ON c.deposit_product_id = dp.deposit_product_id
