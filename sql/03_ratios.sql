-- Module A ratios as a view, so every ratio is one visible formula in SQL.
-- NULLIF turns a zero denominator into NULL, so the ratio is NULL rather than an error.
-- The Python functions in ratios.py use the same formulas; tests check both agree.
-- NETINC is calendar year-to-date (Call Report Schedule RI). A June report covers six months,
-- so the annualisation factor is 12 / month of report_date (June = 2, December = 1).

CREATE OR REPLACE VIEW bank_ratios AS
SELECT
    f.cert,
    i.bank_name,
    f.report_date,
    f.total_assets,
    f.total_equity,
    f.net_loans,
    f.total_deposits,
    f.net_income,
    f.total_equity / NULLIF(f.total_assets, 0)                                   AS equity_to_assets,
    f.net_loans / NULLIF(f.total_deposits, 0)                                    AS loans_to_deposits,
    f.net_income / NULLIF(f.total_assets, 0)                                     AS roa_ytd,
    (12.0 / EXTRACT(MONTH FROM f.report_date)) * f.net_income / NULLIF(f.total_assets, 0)
                                                                                 AS roa_annualised
FROM bank_financials AS f
LEFT JOIN institutions AS i ON i.cert = f.cert;
