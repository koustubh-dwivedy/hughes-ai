WITH source AS (
    SELECT * FROM {{ source('raw', 'funding_events') }}
),

applications AS (
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
    source.funding_id::TEXT              AS funding_id,
    source.application_id::TEXT          AS application_id,
    source.funded_at::TIMESTAMPTZ        AS funded_at,
    source.funded_amount::NUMERIC        AS funded_amount,
    source.created_at::TIMESTAMPTZ       AS created_at,
    product_types.name::TEXT             AS product_type,
    channels.name::TEXT                  AS channel,
    booked_loans.branch_id::INT          AS branch_id,
    booked_loans.officer_id::TEXT        AS officer_id
FROM source
LEFT JOIN applications
    ON source.application_id = applications.application_id
LEFT JOIN product_types
    ON applications.product_type_id = product_types.product_type_id
LEFT JOIN channels
    ON applications.channel_id = channels.channel_id
LEFT JOIN booked_loans
    ON source.application_id = booked_loans.application_id
