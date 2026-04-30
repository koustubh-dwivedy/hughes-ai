SELECT
    m.member_id::TEXT                          AS member_id,
    m.first_name::TEXT                         AS first_name,
    m.last_name::TEXT                          AS last_name,
    (m.first_name || ' ' || m.last_name)::TEXT AS full_name,
    m.joined_at::TIMESTAMPTZ                   AS joined_at,
    b.name::TEXT                               AS home_branch_name,
    b.region::TEXT                             AS home_branch_region
FROM members m
INNER JOIN branches b ON m.home_branch_id = b.branch_id
