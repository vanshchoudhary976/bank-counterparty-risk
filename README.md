# Project F: Bank Counterparty Credit Risk and Early Warning System

A credit analyst's toolkit built on public data. It rates US banks as counterparties, sets and monitors exposure limits, stress-tests them, and values one non-bank company in an Excel model.

**Status: Week 1 (data layer) complete, gate passed with 15 of 15 checks. Modules A to F are not started.**

## Honest limits

- Bank and company financials are real public data (FDIC BankFind, SEC EDGAR).
- The counterparty exposures and collateral terms in later modules will be an **illustrative portfolio** designed for this project. Real trading exposures are not public. This is not clearing or trading experience.
- The scorecard will be trained on US banks. Using it on UK banks is a comparison exercise only.
- This is a learning and portfolio project. It does not claim to meet any regulatory standard.

## Week 1 scope

1. Repository, virtual environment and tests.
2. Download scripts for FDIC (institutions, financials, failures) and SEC company facts. Each run writes a new raw file, never overwrites one, and records a SHA-256 checksum in a manifest.
3. DuckDB schema (`sql/01_schema.sql`) and typed-table build (`sql/02_load_fdic.sql`). Python loads raw values as text into staging tables, and SQL performs every cast, so each conversion is in one visible place.
4. Data checks (`src/credit_risk/checks.py`): row counts reconcile to the API total and across each stage, no duplicate keys in staging, quarter-end dates, no unexpected nulls, non-negative assets, equity not above assets, and the three 2023 failures present.
5. Data dictionary (`docs/data_dictionary.md`). **Field names are provisional until you verify each one against the FDIC data dictionary.**

### Documented exception: equity above assets

One FDIC row breaches the check that total equity does not exceed total assets: certificate 35137, report date 2005-09-30, assets 2,020.0 and equity 2,021.0 (USD thousands). The gap is 1.0, about 0.05% of assets, which looks like rounding at a very small bank. The row stays in the warehouse. The exception is listed in `KNOWN_EQUITY_EXCEPTIONS` in `checks.py`, and the check reports how many exceptions were excluded. Any other breach still fails the build.

## Running it

```bash
make install            # or: python3 -m pip install -r requirements.txt && python3 -m pip install -e .
make test               # unit tests, no network needed
export SEC_USER_AGENT="Your Name you@example.com"
make fdic               # downloads FDIC data to data/raw/fdic/
make sec CIKS="<cik>"   # downloads SEC company facts to data/raw/sec/
make load               # builds data/warehouse.duckdb and runs the checks; exits 1 on any failure
```

## Repository layout

```
sql/                    01_schema.sql, 02_load_fdic.sql
src/credit_risk/        config.py, warehouse.py, checks.py
src/credit_risk/data/   download_fdic.py, download_sec.py, raw_store.py, load_warehouse.py
tests/                  pytest tests for every class (no network)
docs/                   data_dictionary.md, week01_gate.md
data/raw/               downloaded files, never edited (not committed)
data/processed/         extracts for dashboards (later weeks)
```

## Dashboards
Module D interactive dashboard (ILLUSTRATIVE): [Tableau Public](https://public.tableau.com/views/ProjectFModuleDStressResultsILLUSTRATIVE/Dashboard1)


## Principles

- Raw files are never edited. Every load checks the checksum first.
- Every number in a report must be reproducible from code.
- Loads fail loudly. A bad value stops the build rather than being dropped.
