WITH source AS (
    SELECT * FROM {{ source('raw', 'booked_loans') }}
),

branches AS (
    SELECT * FROM {{ source('raw', 'branches') }}
),

product_types AS (
    SELECT * FROM {{ source('raw', 'product_types') }}
)

SELECT
    source.loan_id::TEXT                 AS loan_id,
    source.application_id::TEXT          AS application_id,
    branches.name::TEXT                  AS branch_name,
    branches.region::TEXT                AS branch_region,
    source.member_id::TEXT               AS member_id,
    product_types.name::TEXT             AS product_type,
    source.originated_at::TIMESTAMPTZ    AS originated_at,
    source.original_balance::NUMERIC     AS original_balance,
    source.balance::NUMERIC              AS balance,
    source.rate::NUMERIC                 AS rate,
    source.term_months::INT              AS term_months,
    source.maturity_at::TIMESTAMPTZ      AS maturity_at,
    source.status::TEXT                  AS status,
    source.created_at::TIMESTAMPTZ       AS created_at
FROM source
INNER JOIN branches
    ON source.branch_id = branches.branch_id
INNER JOIN product_types
    ON source.product_type_id = product_types.product_type_id
