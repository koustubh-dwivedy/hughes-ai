WITH source AS (
    SELECT * FROM {{ source('raw', 'applications') }}
),

product_types AS (
    SELECT * FROM {{ source('raw', 'product_types') }}
),

channels AS (
    SELECT * FROM {{ source('raw', 'channels') }}
),

booked_loans AS (
    SELECT * FROM {{ source('raw', 'booked_loans') }}
)

SELECT
    source.application_id::TEXT          AS application_id,
    source.member_id::TEXT               AS member_id,
    product_types.name::TEXT             AS product_type,
    channels.name::TEXT                  AS channel,
    source.requested_amount::NUMERIC     AS requested_amount,
    source.applied_at::TIMESTAMPTZ       AS applied_at,
    source.status::TEXT                  AS status,
    source.created_at::TIMESTAMPTZ       AS created_at,
    booked_loans.branch_id::INT          AS branch_id,
    booked_loans.officer_id::TEXT        AS officer_id
FROM source
INNER JOIN product_types
    ON source.product_type_id = product_types.product_type_id
INNER JOIN channels
    ON source.channel_id = channels.channel_id
LEFT JOIN booked_loans
    ON source.application_id = booked_loans.application_id
