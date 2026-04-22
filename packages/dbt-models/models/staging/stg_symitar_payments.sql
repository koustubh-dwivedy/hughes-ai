WITH source AS (
    SELECT * FROM {{ source('raw', 'payments') }}
)

SELECT
    payment_id::TEXT          AS payment_id,
    loan_id::TEXT             AS loan_id,
    paid_at::TIMESTAMPTZ      AS paid_at,
    amount::NUMERIC           AS amount,
    principal::NUMERIC        AS principal,
    interest::NUMERIC         AS interest,
    payment_method::TEXT      AS payment_method,
    created_at::TIMESTAMPTZ   AS created_at
FROM source
