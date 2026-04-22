{{
    config(materialized='view')
}}

SELECT
    bridge_id::INT                                AS bridge_id,
    application_id::TEXT                          AS application_id,
    loan_id::TEXT                                 AS loan_id,
    match_type::TEXT                              AS match_type,
    CASE match_type
        WHEN 'matched'   THEN 'Direct LOS Match'
        WHEN 'ambiguous' THEN 'Heuristic Match'
        WHEN 'unmatched' THEN 'No Match Found'
    END::TEXT                                     AS match_label,
    (application_id IS NOT NULL)::BOOLEAN         AS has_los_link,
    (loan_id IS NOT NULL)::BOOLEAN                AS has_symitar_link,
    created_at::TIMESTAMPTZ                       AS created_at
FROM {{ source('raw', 'reconciliation_bridge') }}
