SELECT
    segment_code::TEXT                            AS segment_code,
    segment_label::TEXT                           AS segment_label,
    expected_loss_rate_current::NUMERIC           AS expected_loss_rate_current,
    loss_rate_30_59::NUMERIC                      AS loss_rate_30_59,
    loss_rate_60_89::NUMERIC                      AS loss_rate_60_89,
    loss_rate_90_plus::NUMERIC                    AS loss_rate_90_plus,
    qualitative_factors_notes::TEXT               AS qualitative_factors_notes
FROM {{ ref('cecl_segments') }}
