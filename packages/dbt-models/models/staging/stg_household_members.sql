SELECT
    household_member_id::TEXT  AS household_member_id,
    household_id::TEXT         AS household_id,
    member_id::TEXT            AS member_id,
    role::TEXT                 AS role,
    joined_at::TIMESTAMPTZ     AS joined_at,
    left_at::TIMESTAMPTZ       AS left_at
FROM {{ source('raw', 'household_members') }}
