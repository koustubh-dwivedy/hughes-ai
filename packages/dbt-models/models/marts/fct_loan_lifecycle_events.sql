WITH new_events AS (
    SELECT
        DATE_TRUNC('month', fe.funded_at)::DATE          AS as_of_month,
        pt.name::TEXT                                    AS product_type,
        'new'::TEXT                                      AS event_type,
        bl.loan_id::TEXT                                 AS loan_id,
        fe.funded_amount::NUMERIC                        AS amount
    FROM {{ source('raw', 'funding_events') }}           fe
    INNER JOIN {{ source('raw', 'booked_loans') }}       bl ON fe.application_id  = bl.application_id
    INNER JOIN {{ source('raw', 'product_types') }}      pt ON bl.product_type_id = pt.product_type_id
),

paid_off_events AS (
    SELECT
        DATE_TRUNC('month', MAX(lb.snapshot_date))::DATE AS as_of_month,
        pt.name::TEXT                                    AS product_type,
        'paid_off'::TEXT                                 AS event_type,
        bl.loan_id::TEXT                                 AS loan_id,
        bl.original_balance::NUMERIC                     AS amount
    FROM {{ source('raw', 'booked_loans') }}             bl
    INNER JOIN {{ source('raw', 'loan_balances') }}      lb ON bl.loan_id          = lb.loan_id
    INNER JOIN {{ source('raw', 'product_types') }}      pt ON bl.product_type_id  = pt.product_type_id
    WHERE bl.status = 'paid_off'
    GROUP BY bl.loan_id, pt.name, bl.original_balance
),

all_events AS (
    SELECT * FROM new_events
    UNION ALL
    SELECT * FROM paid_off_events
),

grain AS (
    SELECT
        as_of_month,
        product_type,
        event_type,
        COUNT(DISTINCT loan_id)  AS loan_count,
        SUM(amount)              AS total_amount
    FROM all_events
    GROUP BY as_of_month, product_type, event_type
)

SELECT
    g.as_of_month::DATE                                                AS as_of_month,
    g.product_type::TEXT                                               AS product_type,
    g.event_type::TEXT                                                 AS event_type,
    g.loan_count::INT                                                  AS loan_count,
    g.total_amount::NUMERIC                                            AS total_amount,
    (g.as_of_month::TEXT
        || '|' || g.product_type
        || '|' || g.event_type)::TEXT                                 AS row_id
FROM grain g
