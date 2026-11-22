-- Typed warehouse schema. Safe to re-run: every table uses IF NOT EXISTS.
-- Staging tables (stg_institutions, stg_financials, stg_failures) are created by Python
-- as VARCHAR copies of the API response and are not defined here.

CREATE TABLE IF NOT EXISTS institutions (
    cert        INTEGER PRIMARY KEY,
    bank_name   VARCHAR,
    state       VARCHAR,
    active      BOOLEAN
);

-- One row per bank per quarter. Amounts are in thousands of USD, as the FDIC reports them.
-- Confirm units in docs/data_dictionary.md before using any amount in a ratio.
CREATE TABLE IF NOT EXISTS bank_financials (
    cert            INTEGER NOT NULL,
    report_date     DATE NOT NULL,
    total_assets    DOUBLE,
    total_equity    DOUBLE,
    net_loans       DOUBLE,
    total_deposits  DOUBLE,
    net_income      DOUBLE,
    PRIMARY KEY (cert, report_date)
);

-- Every failure in the FDIC list, including the early ones. Banks that failed before deposit
-- insurance existed have no FDIC certificate number, so cert is nullable and there is no primary key.
CREATE TABLE IF NOT EXISTS bank_failures (
    cert        INTEGER,
    bank_name   VARCHAR,
    fail_date   DATE NOT NULL
);

-- Company facts from SEC XBRL. The same period can appear several times (original filing,
-- amendment, later comparative figure), so there is deliberately no primary key here.
CREATE TABLE IF NOT EXISTS sec_facts (
    cik             INTEGER NOT NULL,
    taxonomy        VARCHAR NOT NULL,
    concept         VARCHAR NOT NULL,
    unit            VARCHAR NOT NULL,
    period_end      DATE NOT NULL,
    val             DOUBLE,
    fiscal_year     INTEGER,
    fiscal_period   VARCHAR,
    form            VARCHAR,
    filed           DATE,
    accession       VARCHAR
);

-- One row per staging table per load, so every load can be traced to a raw file and checksum.
CREATE TABLE IF NOT EXISTS load_log (
    table_name       VARCHAR NOT NULL,
    source_file      VARCHAR NOT NULL,
    source_sha256    VARCHAR NOT NULL,
    source_total     INTEGER NOT NULL,
    rows_staged      INTEGER NOT NULL,
    loaded_at        TIMESTAMP DEFAULT current_timestamp
);

-- Week 3 inputs for the scorecard, kept apart from bank_financials so existing loads are unchanged.
-- Percent fields are stored as the FDIC reports them (for example 9.5 means 9.5%). Divided by 100 in the view.
CREATE TABLE IF NOT EXISTS bank_capital_efficiency (
    cert                    INTEGER NOT NULL,
    report_date             DATE NOT NULL,
    tier1_leverage_pct      DOUBLE,
    allowance_for_loans     DOUBLE,
    efficiency_ratio_pct    DOUBLE,
    PRIMARY KEY (cert, report_date)
);
