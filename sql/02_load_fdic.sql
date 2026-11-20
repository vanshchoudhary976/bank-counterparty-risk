-- Builds the typed tables from the staging tables that Python wrote.
-- Staging column names are the FDIC API field names (CERT, REPDTE, ASSET ...), as listed in config.py.
-- TRY_CAST returns NULL on a bad value. The NOT NULL and PRIMARY KEY constraints then make the
-- whole script fail, so a bad value stops the load instead of being silently dropped.
-- The script runs in one transaction. If it fails, nothing is half-written.

BEGIN TRANSACTION;

DELETE FROM institutions;
INSERT INTO institutions (cert, bank_name, state, active)
SELECT
    TRY_CAST(CERT AS INTEGER),
    NAME,
    STALP,
    TRY_CAST(ACTIVE AS INTEGER) = 1
FROM stg_institutions;

DELETE FROM bank_financials;
INSERT INTO bank_financials (cert, report_date, total_assets, total_equity, net_loans, total_deposits, net_income)
SELECT
    TRY_CAST(CERT AS INTEGER),
    TRY_STRPTIME(REPDTE, '%Y%m%d')::DATE,
    TRY_CAST(ASSET AS DOUBLE),
    TRY_CAST(EQTOT AS DOUBLE),
    TRY_CAST(LNLSNET AS DOUBLE),
    TRY_CAST(DEP AS DOUBLE),
    TRY_CAST(NETINC AS DOUBLE)
FROM stg_financials;

-- The FDIC returns FAILDATE as M/D/YYYY (for example 5/28/1934). Some other rows may use ISO dates,
-- so both formats are tried. A value that matches neither becomes NULL and fails the NOT NULL constraint.
-- CERT is NULL for early failures, which is expected and is reported by the checks, not treated as an error.
DELETE FROM bank_failures;
INSERT INTO bank_failures (cert, bank_name, fail_date)
SELECT
    TRY_CAST(CERT AS INTEGER),
    NAME,
    COALESCE(TRY_STRPTIME(FAILDATE, '%m/%d/%Y')::DATE, TRY_CAST(FAILDATE AS DATE))
FROM stg_failures;

COMMIT;
