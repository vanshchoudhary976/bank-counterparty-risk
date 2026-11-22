-- The six scorecard ratios from the blueprint, one or more per CAMELS area. Stored as fractions.
--   Capital:        equity_to_assets, tier1_leverage
--   Asset quality:  allowance_to_loans
--   Earnings:       roa_annualised
--   Efficiency:     efficiency_ratio
--   Liquidity:      loans_to_deposits
-- Allowance to loans uses gross loans (net loans plus the allowance), because LNLSNET is already net of it.
-- Rows with no capital and efficiency data come through as NULL, not zero.

CREATE OR REPLACE VIEW scorecard_inputs AS
SELECT
    r.cert,
    r.report_date,
    r.equity_to_assets,
    c.tier1_leverage_pct / 100.0                                                AS tier1_leverage,
    c.allowance_for_loans / NULLIF(f.net_loans + c.allowance_for_loans, 0)      AS allowance_to_loans,
    r.roa_annualised,
    c.efficiency_ratio_pct / 100.0                                              AS efficiency_ratio,
    r.loans_to_deposits
FROM bank_ratios AS r
JOIN bank_financials AS f ON f.cert = r.cert AND f.report_date = r.report_date
LEFT JOIN bank_capital_efficiency AS c ON c.cert = r.cert AND c.report_date = r.report_date;
