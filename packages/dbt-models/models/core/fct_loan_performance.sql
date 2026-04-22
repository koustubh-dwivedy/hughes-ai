WITH loans AS (
    SELECT * FROM {{ ref('stg_symitar_loans') }}
),

bals AS (
    SELECT
        balance_id::TEXT        AS balance_id,
        loan_id::TEXT           AS loan_id,
        snapshot_date::DATE     AS snapshot_date,
        balance::NUMERIC        AS balance
    FROM {{ source('raw', 'loan_balances') }}
),

delinq AS (
    SELECT * FROM {{ ref('stg_symitar_delinquency') }}
)

SELECT
    bals.loan_id::TEXT                                    AS loan_id,
    bals.snapshot_date::DATE                              AS snapshot_date,
    bals.balance::NUMERIC                                 AS balance,
    loans.status::TEXT                                    AS loan_status,
    COALESCE(delinq.days_past_due, 0)::INT                AS days_past_due,
    delinq.delinquency_bucket::TEXT                       AS delinquency_bucket,
    (COALESCE(delinq.days_past_due, 0) >= 30)::BOOLEAN    AS is_delinquent
FROM bals
INNER JOIN loans  ON bals.loan_id      = loans.loan_id
LEFT  JOIN delinq ON bals.loan_id      = delinq.loan_id
                 AND bals.snapshot_date = delinq.snapshot_date
