WITH delinq_snap AS (
    SELECT
        DATE_TRUNC('month', ds.snapshot_date)::DATE  AS as_of_month,
        bl.officer_id::TEXT                          AS officer_id,
        bl.branch_id::INT                            AS branch_id,
        pt.name::TEXT                                AS product_type,
        ds.loan_id::TEXT                             AS loan_id,
        lb.balance::NUMERIC                          AS balance,
        CASE
            WHEN ds.delinquency_bucket IN ('90-119', '120+') THEN '90+'
            ELSE ds.delinquency_bucket
        END::TEXT                                    AS bucket
    FROM {{ source('raw', 'delinquency_snapshots') }} ds
    INNER JOIN {{ source('raw', 'booked_loans') }}    bl ON ds.loan_id      = bl.loan_id
    INNER JOIN {{ source('raw', 'product_types') }}   pt ON bl.product_type_id = pt.product_type_id
    INNER JOIN {{ source('raw', 'loan_balances') }}   lb ON ds.loan_id      = lb.loan_id
                                                       AND lb.snapshot_date = ds.snapshot_date
    WHERE ds.delinquency_bucket IS NOT NULL
      AND ds.delinquency_bucket != '1-14'
),

grain AS (
    SELECT
        as_of_month,
        officer_id,
        branch_id,
        product_type,
        bucket,
        COUNT(DISTINCT loan_id)                                        AS loan_count,
        SUM(balance)                                                   AS balance,
        SUM(balance) FILTER (WHERE bucket = '90+')                     AS nonaccrual_balance,
        COUNT(DISTINCT CASE WHEN bucket IN ('30-59', '60-89', '90+')
                            THEN loan_id END)                         AS past_due_loan_count
    FROM delinq_snap
    GROUP BY as_of_month, officer_id, branch_id, product_type, bucket
)

SELECT
    g.as_of_month::DATE                                                AS as_of_month,
    g.officer_id::TEXT                                                 AS officer_id,
    g.branch_id::INT                                                   AS branch_id,
    g.product_type::TEXT                                               AS product_type,
    g.bucket::TEXT                                                     AS bucket,
    g.loan_count::INT                                                  AS loan_count,
    g.balance::NUMERIC                                                 AS balance,
    COALESCE(g.nonaccrual_balance, 0)::NUMERIC                         AS nonaccrual_balance,
    g.past_due_loan_count::INT                                         AS past_due_loan_count,
    (g.as_of_month >= DATE_TRUNC('month', CURRENT_DATE)
        - INTERVAL '12 months')::BOOLEAN                              AS is_in_13_month_window,
    (g.as_of_month::TEXT
        || '|' || COALESCE(g.officer_id, 'NULL')
        || '|' || g.product_type
        || '|' || g.bucket)::TEXT                                     AS row_id
FROM grain g
