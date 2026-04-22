WITH source AS (
    SELECT * FROM {{ source('raw', 'delinquency_snapshots') }}
)

SELECT
    snapshot_id::TEXT          AS snapshot_id,
    loan_id::TEXT              AS loan_id,
    snapshot_date::DATE        AS snapshot_date,
    days_past_due::INT         AS days_past_due,
    delinquency_bucket::TEXT   AS delinquency_bucket,
    created_at::TIMESTAMPTZ    AS created_at
FROM source
