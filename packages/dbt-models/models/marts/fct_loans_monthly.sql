WITH loan_snap AS (
    SELECT
        DATE_TRUNC('month', lb.snapshot_date)::DATE  AS as_of_month,
        pt.name::TEXT                                AS product_type,
        bl.branch_id::INT                            AS branch_id,
        bl.officer_id::TEXT                          AS officer_id,
        bl.member_id::TEXT                           AS member_id,
        bl.dealer_id::TEXT                           AS dealer_id,
        ch.name::TEXT                                AS channel,
        lb.balance::NUMERIC                          AS balance,
        bl.rate::NUMERIC                             AS rate,
        bl.loan_id::TEXT                             AS loan_id
    FROM {{ source('raw', 'loan_balances') }}       lb
    INNER JOIN {{ source('raw', 'booked_loans') }}  bl ON lb.loan_id = bl.loan_id
    INNER JOIN {{ source('raw', 'product_types') }} pt ON bl.product_type_id = pt.product_type_id
    LEFT  JOIN {{ source('raw', 'applications') }}  app ON bl.application_id = app.application_id
    LEFT  JOIN {{ source('raw', 'channels') }}      ch  ON app.channel_id = ch.channel_id
),

member_loan_cnt AS (
    SELECT
        as_of_month, product_type, branch_id, officer_id, channel, member_id,
        COUNT(DISTINCT loan_id) AS loans_in_group
    FROM loan_snap
    GROUP BY as_of_month, product_type, branch_id, officer_id, channel, member_id
),

grain AS (
    SELECT
        as_of_month,
        product_type,
        branch_id,
        officer_id,
        channel,
        dealer_id,
        COUNT(DISTINCT loan_id)                       AS loan_count,
        SUM(balance)                                  AS total_balance,
        AVG(balance)                                  AS avg_balance,
        COALESCE(SUM(balance * rate) / NULLIF(SUM(balance), 0), 0) AS weighted_avg_rate
    FROM loan_snap
    GROUP BY as_of_month, product_type, branch_id, officer_id, channel, dealer_id
),

single_loan AS (
    SELECT
        as_of_month, product_type, branch_id, officer_id, channel,
        COUNT(DISTINCT member_id) AS single_loan_customer_count
    FROM member_loan_cnt
    WHERE loans_in_group = 1
    GROUP BY as_of_month, product_type, branch_id, officer_id, channel
)

SELECT
    g.as_of_month::DATE                                               AS as_of_month,
    g.product_type::TEXT                                              AS product_type,
    g.branch_id::INT                                                  AS branch_id,
    g.officer_id::TEXT                                                AS officer_id,
    g.channel::TEXT                                                   AS channel,
    g.dealer_id::TEXT                                                 AS dealer_id,
    g.loan_count::INT                                                 AS loan_count,
    g.total_balance::NUMERIC                                          AS total_balance,
    g.avg_balance::NUMERIC                                            AS avg_balance,
    g.weighted_avg_rate::NUMERIC                                      AS weighted_avg_rate,
    COALESCE(s.single_loan_customer_count, 0)::INT                    AS single_loan_customer_count,
    (g.as_of_month::TEXT || '|' || g.product_type
        || '|' || g.branch_id::TEXT
        || '|' || COALESCE(g.officer_id, 'NULL')
        || '|' || COALESCE(g.channel, 'NULL')
        || '|' || COALESCE(g.dealer_id, 'NULL'))::TEXT                AS row_id
FROM grain g
LEFT JOIN single_loan s
       ON  g.as_of_month  = s.as_of_month
      AND  g.product_type = s.product_type
      AND  g.branch_id    = s.branch_id
      AND  (g.officer_id  = s.officer_id
            OR (g.officer_id IS NULL AND s.officer_id IS NULL))
      AND  (g.channel = s.channel
            OR (g.channel IS NULL AND s.channel IS NULL))
