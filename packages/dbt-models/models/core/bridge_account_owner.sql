SELECT
    owner_id,
    owner_kind,
    owner_account_id,
    member_id,
    role,
    since_at,
    until_at,
    (until_at IS NULL)::BOOLEAN AS is_current
FROM {{ ref('stg_account_owners') }}
