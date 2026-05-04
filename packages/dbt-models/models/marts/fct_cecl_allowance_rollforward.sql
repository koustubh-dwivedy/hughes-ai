-- CECL allowance roll-forward by (month, segment).
--
-- Methodology (simplified — see docs/metrics.md for the full caveat):
--   expected_allowance(t, seg) = Σ over loans in segment of
--     balance × loss_rate_for_DPD_band
--   ending_balance(t)          = expected_allowance(t)
--   provision_expense(t)       = ending_balance(t) - (beginning_balance - NCO)
--   net_charge_offs            = charge_offs - recoveries
--   charge_offs                = balance of loans that transitioned to
--                                 charged_off in month t (heuristic — last
--                                 snapshot month for status='charged_off')
--   recoveries                 = 0.20 × prior-month charge_offs
--                                (industry rule-of-thumb)
--
-- Closure invariant (zero tolerance, asserted in the audit harness):
--   ending_balance(t) = beginning_balance(t) - net_charge_offs(t)
--                     + provision_expense(t)

WITH segments AS (
    SELECT * FROM {{ ref('dim_cecl_segment') }}
),

loan_perf_with_segment AS (
    SELECT
        perf.snapshot_date,
        perf.loan_id,
        perf.balance,
        perf.days_past_due,
        loan.cecl_segment_code,
        loan.status,
        CASE
            WHEN perf.days_past_due >= 90 THEN 'loss_rate_90_plus'
            WHEN perf.days_past_due >= 60 THEN 'loss_rate_60_89'
            WHEN perf.days_past_due >= 30 THEN 'loss_rate_30_59'
            ELSE 'expected_loss_rate_current'
        END AS dpd_band
    FROM {{ ref('fct_loan_performance') }} perf
    INNER JOIN {{ ref('dim_loan') }} loan USING (loan_id)
    WHERE loan.cecl_segment_code IS NOT NULL
),

expected_by_segment AS (
    SELECT
        DATE_TRUNC('month', lp.snapshot_date)::DATE AS period_end_month,
        lp.cecl_segment_code,
        SUM(
            lp.balance * CASE lp.dpd_band
                WHEN 'expected_loss_rate_current' THEN seg.expected_loss_rate_current
                WHEN 'loss_rate_30_59'           THEN seg.loss_rate_30_59
                WHEN 'loss_rate_60_89'           THEN seg.loss_rate_60_89
                ELSE seg.loss_rate_90_plus
            END
        ) AS expected_allowance
    FROM loan_perf_with_segment lp
    INNER JOIN segments seg ON seg.segment_code = lp.cecl_segment_code
    GROUP BY 1, 2
),

charge_offs_by_segment AS (
    -- Heuristic: a charged_off loan's "charge-off month" is the latest
    -- snapshot we have for it, after which the balance falls to ~0.
    SELECT
        DATE_TRUNC('month', last_snap.snapshot_date)::DATE AS period_end_month,
        loan.cecl_segment_code,
        SUM(last_snap.balance) AS charge_offs
    FROM (
        SELECT
            loan_id,
            MAX(snapshot_date) AS snapshot_date,
            MAX(balance)        AS balance
        FROM {{ ref('fct_loan_performance') }}
        GROUP BY loan_id
    ) AS last_snap_meta
    INNER JOIN LATERAL (
        SELECT snapshot_date, balance
        FROM {{ ref('fct_loan_performance') }}
        WHERE loan_id = last_snap_meta.loan_id
          AND snapshot_date = last_snap_meta.snapshot_date
        LIMIT 1
    ) AS last_snap ON TRUE
    INNER JOIN {{ ref('dim_loan') }} loan USING (loan_id)
    WHERE loan.status = 'charged_off'
      AND loan.cecl_segment_code IS NOT NULL
    GROUP BY 1, 2
),

months_segments AS (
    -- Cartesian product of every month present in expected_by_segment
    -- with every segment, so we get a row even when a segment has no
    -- charge-offs / recoveries that month.
    SELECT DISTINCT period_end_month, segment_code AS cecl_segment_code
    FROM expected_by_segment
    CROSS JOIN segments
),

joined AS (
    SELECT
        ms.period_end_month,
        ms.cecl_segment_code,
        COALESCE(eb.expected_allowance, 0)::NUMERIC AS expected_allowance,
        COALESCE(co.charge_offs,        0)::NUMERIC AS charge_offs
    FROM months_segments ms
    LEFT JOIN expected_by_segment eb
        ON ms.period_end_month   = eb.period_end_month
       AND ms.cecl_segment_code  = eb.cecl_segment_code
    LEFT JOIN charge_offs_by_segment co
        ON ms.period_end_month   = co.period_end_month
       AND ms.cecl_segment_code  = co.cecl_segment_code
),

with_recoveries AS (
    SELECT
        period_end_month,
        cecl_segment_code,
        expected_allowance,
        charge_offs,
        -- Recoveries = 20% of the prior-month charge-offs in the same segment.
        COALESCE(LAG(charge_offs, 1) OVER (
            PARTITION BY cecl_segment_code ORDER BY period_end_month
        ), 0) * 0.20 AS recoveries
    FROM joined
),

with_balances AS (
    SELECT
        period_end_month,
        cecl_segment_code,
        expected_allowance AS ending_balance,
        charge_offs,
        recoveries,
        (charge_offs - recoveries) AS net_charge_offs,
        COALESCE(LAG(expected_allowance, 1) OVER (
            PARTITION BY cecl_segment_code ORDER BY period_end_month
        ), 0)::NUMERIC AS beginning_balance
    FROM with_recoveries
)

SELECT
    period_end_month,
    cecl_segment_code,
    beginning_balance,
    charge_offs,
    recoveries,
    net_charge_offs,
    -- Provision is the plug that closes the roll-forward.
    (ending_balance - beginning_balance + net_charge_offs)::NUMERIC AS provision_expense,
    ending_balance,
    CASE WHEN ending_balance > 0
         THEN net_charge_offs / NULLIF(ending_balance, 0)
         ELSE 0 END::NUMERIC AS coverage_ratio_dpd60
FROM with_balances
ORDER BY period_end_month, cecl_segment_code
