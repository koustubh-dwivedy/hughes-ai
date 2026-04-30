SELECT
    deposit_product_id::TEXT                                         AS deposit_product_id,
    name::TEXT                                                       AS product_name,
    is_core_deposit::BOOLEAN                                         AS is_core_deposit,
    CASE WHEN is_core_deposit THEN 'Core' ELSE 'Non-Core' END::TEXT  AS deposit_category
FROM deposit_products
