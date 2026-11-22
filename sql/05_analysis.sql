-- Week 2 peer groups and analysis queries.
-- Amounts are in thousands of USD, so the size bands below are written in thousands:
-- $1bn = 1,000,000; $10bn = 10,000,000; $100bn = 100,000,000.
-- Each bank-quarter is placed in a size band by its own total assets in that quarter.
-- Bands are for comparing like with like. They are not regulatory categories.

CREATE OR REPLACE VIEW peer_group_quarters AS
SELECT
    r.*,
    CASE
        WHEN r.total_assets IS NULL THEN NULL
        WHEN r.total_assets < 1000000 THEN 'a: under $1bn'
        WHEN r.total_assets < 10000000 THEN 'b: $1bn to $10bn'
        WHEN r.total_assets < 100000000 THEN 'c: $10bn to $100bn'
        ELSE 'd: over $100bn'
    END AS size_band,
    EXTRACT(YEAR FROM r.report_date) AS report_year
FROM bank_ratios AS r;

-- Query 1: median equity to assets by size band and year.
CREATE OR REPLACE VIEW analysis_equity_to_assets_by_band AS
SELECT size_band, report_year, COUNT(*) AS bank_quarters,
       MEDIAN(equity_to_assets) AS median_equity_to_assets
FROM peer_group_quarters
WHERE size_band IS NOT NULL AND equity_to_assets IS NOT NULL
GROUP BY size_band, report_year
ORDER BY size_band, report_year;

-- Query 2: median annualised ROA by size band and year.
CREATE OR REPLACE VIEW analysis_roa_by_band_year AS
SELECT size_band, report_year, COUNT(*) AS bank_quarters,
       MEDIAN(roa_annualised) AS median_roa_annualised
FROM peer_group_quarters
WHERE size_band IS NOT NULL AND roa_annualised IS NOT NULL
GROUP BY size_band, report_year
ORDER BY size_band, report_year;

-- Query 3: share of banks whose loans are larger than their deposits, by size band and year.
CREATE OR REPLACE VIEW analysis_loans_above_deposits_by_band AS
SELECT size_band, report_year, COUNT(loans_to_deposits) AS bank_quarters,
       SUM(CASE WHEN loans_to_deposits > 1 THEN 1 ELSE 0 END) * 1.0 / COUNT(loans_to_deposits)
           AS share_loans_above_deposits
FROM peer_group_quarters
WHERE size_band IS NOT NULL AND loans_to_deposits IS NOT NULL
GROUP BY size_band, report_year
ORDER BY size_band, report_year;

-- Query 4: failures by year and size band. Each failure is placed in the band of the bank's
-- last report before the failure date. Failures with no CERT or no earlier report are left out.
CREATE OR REPLACE VIEW analysis_failures_by_band_year AS
WITH failures AS (
    SELECT cert, fail_date FROM bank_failures WHERE cert IS NOT NULL
),
last_report AS (
    SELECT f.cert, f.fail_date, p.size_band,
           ROW_NUMBER() OVER (PARTITION BY f.cert, f.fail_date ORDER BY p.report_date DESC) AS rn
    FROM failures AS f
    JOIN peer_group_quarters AS p ON p.cert = f.cert AND p.report_date < f.fail_date
)
SELECT EXTRACT(YEAR FROM fail_date) AS fail_year, size_band, COUNT(*) AS failures
FROM last_report
WHERE rn = 1 AND size_band IS NOT NULL
GROUP BY fail_year, size_band
ORDER BY fail_year, size_band;

-- Query 5: banks with equity to assets below 5% in the latest report date in the data.
CREATE OR REPLACE VIEW analysis_low_capital_latest AS
SELECT cert, bank_name, report_date, equity_to_assets, size_band
FROM peer_group_quarters
WHERE report_date = (SELECT MAX(report_date) FROM bank_financials)
  AND equity_to_assets < 0.05
ORDER BY equity_to_assets;
