WITH loans AS (
    SELECT * FROM {{ ref('stg_symitar_loans') }}
),

recon AS (
    SELECT * FROM {{ ref('recon_bridge') }}
    WHERE match_type = 'matched'
),

apps AS (
    SELECT * FROM {{ ref('stg_origence_applications') }}
)

SELECT
    loans.loan_id::TEXT                             AS loan_id,
    loans.product_type::TEXT                        AS product_type,
    COALESCE(apps.channel, 'unknown')::TEXT         AS channel,
    loans.branch_id::INT                            AS branch_id,
    loans.branch_name::TEXT                         AS branch_name,
    loans.branch_region::TEXT                       AS branch_region,
    loans.dealer_id::TEXT                           AS dealer_id,
    loans.dealer_reserve_amount::NUMERIC            AS dealer_reserve_amount,
    'fixed'::TEXT                                   AS rate_type,
    loans.rate::NUMERIC                             AS rate,
    loans.term_months::INT                          AS term_months,
    loans.originated_at::TIMESTAMPTZ                AS originated_at,
    loans.maturity_at::TIMESTAMPTZ                  AS maturity_at,
    loans.status::TEXT                              AS status,
    -- NCUA 5300 line code (Schedule CB) + CECL segment
    -- mapped from product_type. Source of truth: products.yaml.
    CASE loans.product_type
        WHEN 'auto_direct'    THEN '396_direct'
        WHEN 'auto_indirect'  THEN '396_indirect'
        WHEN 'first_mortgage' THEN '703a'
        WHEN 'heloc'          THEN '703b_revolving'
        WHEN 'closed_end_2nd' THEN '703b_closed'
        WHEN 'credit_card'    THEN '396a'
        ELSE NULL
    END::TEXT                                       AS ncua_5300_line_code,
    CASE loans.product_type
        WHEN 'auto_direct'    THEN 'consumer_auto'
        WHEN 'auto_indirect'  THEN 'consumer_auto'
        WHEN 'first_mortgage' THEN 'real_estate_1st'
        WHEN 'heloc'          THEN 'real_estate_junior'
        WHEN 'closed_end_2nd' THEN 'real_estate_junior'
        WHEN 'credit_card'    THEN 'credit_card'
        ELSE NULL
    END::TEXT                                       AS cecl_segment_code
FROM loans
LEFT JOIN recon ON loans.loan_id          = recon.loan_id
LEFT JOIN apps  ON recon.application_id   = apps.application_id
