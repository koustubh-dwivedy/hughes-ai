SELECT
    name        AS product_type_name,
    name        AS product_type,
    created_at  AS created_at
FROM {{ source('raw', 'product_types') }}
