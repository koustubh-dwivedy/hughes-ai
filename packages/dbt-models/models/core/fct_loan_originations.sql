WITH recon AS (
    SELECT * FROM {{ ref('recon_bridge') }}
    WHERE match_type = 'matched'
),

apps AS (
    SELECT * FROM {{ ref('stg_origence_applications') }}
),

funds AS (
    SELECT * FROM {{ ref('stg_origence_fundings') }}
),

loans AS (
    SELECT * FROM {{ ref('stg_symitar_loans') }}
)

SELECT
    loans.loan_id::TEXT                 AS loan_id,
    apps.application_id::TEXT           AS application_id,
    apps.member_id::TEXT                AS member_id,
    apps.product_type::TEXT             AS product_type,
    apps.channel::TEXT                  AS channel,
    loans.branch_name::TEXT             AS branch_name,
    loans.branch_region::TEXT           AS branch_region,
    apps.applied_at::TIMESTAMPTZ        AS applied_at,
    funds.funded_at::TIMESTAMPTZ        AS funded_at,
    loans.originated_at::TIMESTAMPTZ    AS originated_at,
    apps.requested_amount::NUMERIC      AS requested_amount,
    funds.funded_amount::NUMERIC        AS funded_amount,
    loans.original_balance::NUMERIC     AS original_balance,
    loans.rate::NUMERIC                 AS rate,
    loans.term_months::INT              AS term_months,
    loans.maturity_at::TIMESTAMPTZ      AS maturity_at,
    loans.status::TEXT                  AS loan_status,
    recon.match_type::TEXT              AS match_type
FROM recon
INNER JOIN funds ON recon.application_id = funds.application_id
INNER JOIN apps  ON recon.application_id = apps.application_id
INNER JOIN loans ON recon.loan_id        = loans.loan_id
