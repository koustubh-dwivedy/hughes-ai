SELECT
    dealer_id           AS dealer_id,
    dealer_name         AS dealer_name,
    dealer_type         AS dealer_type,
    address_city        AS address_city,
    address_state       AS address_state,
    markup_tier         AS markup_tier,
    active_from         AS active_from,
    active_until        AS active_until,
    (active_until IS NULL)::BOOLEAN  AS is_active
FROM {{ ref('stg_dealers') }}
