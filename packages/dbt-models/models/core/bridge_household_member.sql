SELECT
    household_member_id,
    household_id,
    member_id,
    role,
    joined_at,
    left_at,
    (left_at IS NULL)::BOOLEAN AS is_current
FROM {{ ref('stg_household_members') }}
