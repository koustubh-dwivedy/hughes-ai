SELECT
    balance_id::TEXT     AS balance_id,
    loan_id::TEXT        AS loan_id,
    snapshot_date::DATE  AS snapshot_date,
    balance::NUMERIC     AS balance,
    credit_limit::NUMERIC AS credit_limit
FROM {{ source('raw', 'card_balances') }}
