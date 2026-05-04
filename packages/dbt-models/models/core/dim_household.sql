WITH households AS (
    SELECT * FROM {{ ref('stg_households') }}
),

member_counts AS (
    SELECT
        household_id,
        COUNT(*) AS total_members,
        SUM(CASE WHEN role = 'primary' THEN 1 ELSE 0 END)   AS primary_count,
        SUM(CASE WHEN role = 'joint' THEN 1 ELSE 0 END)     AS joint_count,
        SUM(CASE WHEN role = 'dependent' THEN 1 ELSE 0 END) AS dependent_count
    FROM {{ ref('stg_household_members') }}
    WHERE left_at IS NULL
    GROUP BY household_id
)

SELECT
    h.household_id,
    h.household_name,
    h.primary_member_id,
    h.formed_at,
    h.dissolved_at,
    (h.dissolved_at IS NULL)::BOOLEAN AS is_active,
    COALESCE(mc.total_members, 0)     AS total_members,
    COALESCE(mc.primary_count, 0)     AS primary_count,
    COALESCE(mc.joint_count, 0)       AS joint_count,
    COALESCE(mc.dependent_count, 0)   AS dependent_count,
    CASE
        WHEN COALESCE(mc.total_members, 0) >= 3 THEN 'multi_generation'
        WHEN COALESCE(mc.total_members, 0) = 2  THEN 'paired'
        ELSE 'single'
    END::TEXT AS household_type
FROM households h
LEFT JOIN member_counts mc ON h.household_id = mc.household_id
