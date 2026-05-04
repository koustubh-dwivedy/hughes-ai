SELECT
    owner_id::TEXT            AS owner_id,
    owner_kind::TEXT          AS owner_kind,
    owner_account_id::TEXT    AS owner_account_id,
    member_id::TEXT           AS member_id,
    role::TEXT                AS role,
    since::TIMESTAMPTZ        AS since_at,
    until_ts::TIMESTAMPTZ     AS until_at
FROM {{ source('raw', 'account_owners') }}
