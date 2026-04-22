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
    loans.branch_name::TEXT                         AS branch_name,
    loans.branch_region::TEXT                       AS branch_region,
    'fixed'::TEXT                                   AS rate_type,
    loans.rate::NUMERIC                             AS rate,
    loans.term_months::INT                          AS term_months,
    loans.originated_at::TIMESTAMPTZ                AS originated_at,
    loans.maturity_at::TIMESTAMPTZ                  AS maturity_at,
    loans.status::TEXT                              AS status
FROM loans
LEFT JOIN recon ON loans.loan_id          = recon.loan_id
LEFT JOIN apps  ON recon.application_id   = apps.application_id
