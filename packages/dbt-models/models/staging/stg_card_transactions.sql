SELECT
    transaction_id::TEXT      AS transaction_id,
    loan_id::TEXT             AS loan_id,
    occurred_at::TIMESTAMPTZ  AS occurred_at,
    amount::NUMERIC           AS amount,
    txn_type::TEXT            AS txn_type,
    merchant_category::TEXT   AS merchant_category
FROM {{ source('raw', 'card_transactions') }}
