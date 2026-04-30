SELECT
    o.officer_id::TEXT       AS officer_id,
    o.name::TEXT             AS officer_name,
    o.hired_at::TIMESTAMPTZ  AS hired_at,
    o.status::TEXT           AS status,
    b.name::TEXT             AS branch_name,
    b.region::TEXT           AS branch_region
FROM officers o
INNER JOIN branches b ON o.branch_id = b.branch_id
