SELECT
    household_id::TEXT         AS household_id,
    household_name::TEXT       AS household_name,
    primary_member_id::TEXT    AS primary_member_id,
    formed_at::TIMESTAMPTZ     AS formed_at,
    dissolved_at::TIMESTAMPTZ  AS dissolved_at
FROM {{ source('raw', 'households') }}
