SELECT
    deposit_product_id::TEXT                                         AS deposit_product_id,
    name::TEXT                                                       AS product_name,
    is_core_deposit::BOOLEAN                                         AS is_core_deposit,
    CASE WHEN is_core_deposit THEN 'Core' ELSE 'Non-Core' END::TEXT  AS deposit_category,
    -- NCUA 5300 Schedule CB line code per share product. Source of
    -- truth: packages/synth-data/profiles/products.yaml.
    CASE name
        WHEN 'Demand'           THEN '902'
        WHEN 'Savings'          THEN '903'
        WHEN 'Money Market'     THEN '911'
        WHEN 'Interest Bearing' THEN '912'
        WHEN 'Time Deposits'    THEN '908'
        ELSE NULL
    END::TEXT                                                        AS ncua_5300_line_code
FROM deposit_products
