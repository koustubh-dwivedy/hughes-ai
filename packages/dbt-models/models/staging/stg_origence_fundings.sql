WITH source AS (
    SELECT * FROM {{ source('raw', 'funding_events') }}
)

SELECT
    funding_id::TEXT          AS funding_id,
    application_id::TEXT      AS application_id,
    funded_at::TIMESTAMPTZ    AS funded_at,
    funded_amount::NUMERIC    AS funded_amount,
    created_at::TIMESTAMPTZ   AS created_at
FROM source
