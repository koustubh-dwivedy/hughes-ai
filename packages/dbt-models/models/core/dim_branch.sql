SELECT
    branch_id   AS branch_id,
    name        AS branch_name,
    region      AS branch_region,
    created_at  AS created_at
FROM {{ source('raw', 'branches') }}
