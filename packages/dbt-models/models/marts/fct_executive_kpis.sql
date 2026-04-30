WITH monthly_loans AS (
    SELECT
        as_of_month,
        SUM(total_balance)                                                 AS total_loans_balance,
        SUM(total_balance * weighted_avg_rate)
            / NULLIF(SUM(total_balance), 0)                               AS weighted_avg_loan_rate
    FROM {{ ref('fct_loans_monthly') }}
    GROUP BY as_of_month
),

monthly_deposits AS (
    SELECT
        as_of_month,
        SUM(total_balance)                                                 AS total_deposits_balance,
        SUM(CASE WHEN is_core_deposit THEN total_balance ELSE 0 END)
            / NULLIF(SUM(total_balance), 0)                               AS core_deposit_ratio,
        SUM(total_balance * CASE WHEN is_core_deposit THEN 0.015
                                  ELSE 0.035 END)
            / NULLIF(SUM(total_balance), 0)                               AS weighted_avg_deposit_rate
    FROM {{ ref('fct_deposits_monthly') }}
    GROUP BY as_of_month
),

monthly_delinquency AS (
    SELECT
        as_of_month,
        SUM(CASE WHEN bucket IN ('30-59', '60-89', '90+')
                 THEN balance ELSE 0 END)                                 AS past_due_balance
    FROM {{ ref('fct_delinquency_monthly') }}
    GROUP BY as_of_month
),

spine AS (
    SELECT
        l.as_of_month,
        l.total_loans_balance,
        l.weighted_avg_loan_rate,
        d.total_deposits_balance,
        d.core_deposit_ratio,
        d.weighted_avg_deposit_rate,
        COALESCE(dq.past_due_balance, 0)                                  AS past_due_balance
    FROM monthly_loans               l
    INNER JOIN monthly_deposits      d  USING (as_of_month)
    LEFT  JOIN monthly_delinquency   dq USING (as_of_month)
),

with_kpis AS (
    SELECT
        as_of_month,
        total_loans_balance,
        total_deposits_balance,
        core_deposit_ratio,
        weighted_avg_loan_rate,
        weighted_avg_deposit_rate,
        total_loans_balance / NULLIF(total_deposits_balance, 0)           AS loan_to_deposit_ratio,
        past_due_balance    / NULLIF(total_loans_balance, 0)              AS blended_past_due_ratio,
        weighted_avg_loan_rate - weighted_avg_deposit_rate                AS rate_spread,
        total_loans_balance
            - LAG(total_loans_balance, 1, total_loans_balance)
              OVER (ORDER BY as_of_month)                                 AS monthly_loan_growth,
        total_deposits_balance
            - LAG(total_deposits_balance, 1, total_deposits_balance)
              OVER (ORDER BY as_of_month)                                 AS monthly_deposit_growth
    FROM spine
)

SELECT
    as_of_month::DATE                                                      AS as_of_month,
    total_loans_balance::NUMERIC                                           AS total_loans_balance,
    total_deposits_balance::NUMERIC                                        AS total_deposits_balance,
    loan_to_deposit_ratio::NUMERIC                                         AS loan_to_deposit_ratio,
    core_deposit_ratio::NUMERIC                                            AS core_deposit_ratio,
    blended_past_due_ratio::NUMERIC                                        AS blended_past_due_ratio,
    monthly_loan_growth::NUMERIC                                           AS monthly_loan_growth,
    monthly_deposit_growth::NUMERIC                                        AS monthly_deposit_growth,
    weighted_avg_loan_rate::NUMERIC                                        AS weighted_avg_loan_rate,
    weighted_avg_deposit_rate::NUMERIC                                     AS weighted_avg_deposit_rate,
    rate_spread::NUMERIC                                                   AS rate_spread,
    as_of_month::TEXT                                                      AS row_id
FROM with_kpis
