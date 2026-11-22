-- Cleaned scorecard inputs (cleaning rules decided 22 November 2026, see docs/ratio_definitions.md).
--   Rule 1: zero deposits and zero net loans, dropped.
--   Rule 2: equity above total assets, dropped.
--   Rule 6: Tier 1 leverage above 50% or equity above half of total assets, dropped.
--   Rule 3: negative equity on a normal balance sheet, kept (not filtered here).
--   Rule 4: efficiency ratio exactly 0, set to NULL (treated as missing, not dropped).
-- Rule 5 (caps at development percentiles) is applied in Python, because the caps come from development data.

CREATE OR REPLACE VIEW clean_scorecard_inputs AS
SELECT
    s.cert,
    s.report_date,
    s.equity_to_assets,
    s.tier1_leverage,
    s.allowance_to_loans,
    s.roa_annualised,
    CASE WHEN c.efficiency_ratio_pct = 0 THEN NULL ELSE s.efficiency_ratio END AS efficiency_ratio,
    s.loans_to_deposits
FROM scorecard_inputs AS s
JOIN bank_financials AS f ON f.cert = s.cert AND f.report_date = s.report_date
LEFT JOIN bank_capital_efficiency AS c ON c.cert = s.cert AND c.report_date = s.report_date
WHERE NOT COALESCE(
    (COALESCE(f.total_deposits, 0) = 0 AND COALESCE(f.net_loans, 0) = 0)
    OR (f.total_equity > f.total_assets)
    OR (c.tier1_leverage_pct > 50)
    OR (f.total_equity > 0.5 * f.total_assets),
    FALSE
);
