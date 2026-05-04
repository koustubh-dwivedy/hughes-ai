SELECT
    dealer_id::TEXT          AS dealer_id,
    name::TEXT               AS dealer_name,
    dealer_type::TEXT        AS dealer_type,
    address_city::TEXT       AS address_city,
    address_state::TEXT      AS address_state,
    markup_tier::TEXT        AS markup_tier,
    active_from::TIMESTAMPTZ AS active_from,
    active_until::TIMESTAMPTZ AS active_until
FROM {{ source('raw', 'dealers') }}
