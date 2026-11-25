# Project F: Bank Counterparty Credit Risk and Early Warning System

A credit analyst's toolkit built on public data. It rates US banks as counterparties, sets and monitors exposure limits on an illustrative portfolio, stress-tests the banks, writes credit committee memos, and values one non-bank company (Costco) in an Excel model.

**Status: All modules (A to F) complete. Two gates were not met, and the results are reported as they are.**

## Honest limits

- Bank and company financials are real public data (FDIC BankFind, SEC EDGAR).
- The counterparty exposures and collateral terms are an **illustrative portfolio** designed for this project. Real trading exposures are not public. This is not clearing or trading experience.
- The scorecard is trained on US banks. Using it on UK banks would be a comparison exercise only.
- The three credit committee memos are illustrative exercises, not real credit decisions.
- This is a learning and portfolio project. It does not claim to meet any regulatory standard.

## Results

| Module | What it does | Result | Gate |
|---|---|---|---|
| Week 1: Data layer | Downloads and checks FDIC and SEC data | 15 of 15 checks passed | Passed |
| B: Scorecard | Rates banks on six inputs with logistic regression | Blueprint test set (2014 to 2022 Q3) scored once; result failed. Substitute: rolling out-of-time check on 2011 to 2013 | Not met |
| C: Exposure engine | Netting, collateral and limits for 12 banks, expected loss at LGD 25%, 45% and 60% | Netting, collateral and seed tests pass | Met |
| D: Stress tests | Four scenarios: deposit run, credit shock, rate shock, combined | Early-warning rule (grade 8 or worse) flags 27.7% of survivor quarters in 2008 to 2012; quarterly false alarm rate 29.1% (2008 to 2012) and 19.4% (2023 cases) | Early-warning gate not met |
| E: Credit memos | Three illustrative committee memos (SVB, JPMorgan Chase, Texas Bank and Trust) | Recommendations: hold, approve placeholder limit, monitor | Complete |
| F: Company model | Excel DCF for Costco with scenarios and sensitivity tables | Base-case value $302.74 per share at WACC 8.75% and terminal growth 2.0% | Complete (illustrative) |

The early-warning thresholds were not changed after the back-test. Changing them now would bias the result, because they would be tuned on data already seen. The full record of changes is in `docs/change_log.md`.

## Data sources

- **FDIC BankFind:** institutions, quarterly financials and bank failures.
- **SEC EDGAR company facts:** financial statements for the non-bank company in Module F.
- **Yahoo Finance:** beta for Module F (0.87, 28 July 2026).

## Method

- **Cleaning:** six documented rules on the raw FDIC fields, applied in SQL, plus winsorising each input at the development-period 1st and 99th percentiles.
- **Scorecard:** logistic regression with six inputs, C = 1.0, standardised after winsorising. Grade cut-offs are built from development-period PDs only.
- **Expected loss:** EAD x PD x LGD, with LGD 45% and a PD floor of 0.05%.
- **Valuation:** free cash flow to the firm, end-year discounting, Gordon growth terminal value.

## Limitations

- **Early-warning rule.** Fails its gate. It is recorded as a limitation, not tuned.
- **Test window.** No test window with enough failures exists in the current data. The rolling check reuses data already seen during development, so it is weaker than the blueprint test.
- **Asset quality.** Non-performing loans and charge-offs are not in the warehouse, so they are not used.
- **Return on assets.** The annualised figure is taken from the warehouse column and has not been reconciled to net income for every quarter.
- **Units.** Values are assumed to be in thousands of US dollars. This is consistent with the data but should be confirmed against the FDIC data dictionary.
- **PD floor.** The 0.05% floor is a limitation for the lowest-risk banks.

## Reproducing the results

```bash
make install            # installs requirements and the project package
export SEC_USER_AGENT="Your Name you@example.com"
make fdic               # downloads FDIC institutions, financials and failures to data/raw/fdic/
make sec CIKS="<cik>"   # downloads SEC company facts to data/raw/sec/ (one or more CIKs, space-separated)
make load               # builds data/warehouse.duckdb from the raw files and runs the checks; exits 1 on any failure
make test               # unit tests, no network needed
make all                # runs make test, then make load (it does not download data)
```

From a clean clone, run `make install`, then `make fdic` and `make sec`, then `make load` to build the warehouse. `make all` only runs the tests and the load, so it needs the raw files to exist first.

## Data exception: equity above assets

One FDIC row breaches the check that total equity does not exceed total assets: certificate 35137, report date 2005-09-30, assets 2,020.0 and equity 2,021.0 (USD thousands). The gap is 1.0, about 0.05% of assets, which looks like rounding at a very small bank. The row stays in the warehouse. The exception is listed in `KNOWN_EQUITY_EXCEPTIONS` in `checks.py`, and the check reports how many exceptions were excluded. Any other breach still fails the build.

## Dashboards

- Module D stress results (ILLUSTRATIVE): [Tableau Public](https://public.tableau.com/views/ProjectFModuleDStressResultsILLUSTRATIVE/Dashboard1)
- Module F valuation sensitivity (ILLUSTRATIVE): https://public.tableau.com/views/module_f_valuation_sensitivity/module_f_valuation_sensitivity

## Repository layout

```
sql/                    01_schema.sql, 02_load_fdic.sql
src/credit_risk/        config.py, warehouse.py, checks.py
src/credit_risk/data/   download_fdic.py, download_sec.py, raw_store.py, load_warehouse.py
tests/                  pytest tests for every class (no network)
docs/                   data_dictionary.md, week01_gate.md, change_log.md, memos
excel/                  company_model.xlsx (Module F)
reports/tableau/        CSV extracts for the dashboards
data/raw/               downloaded files, never edited (not committed)
data/processed/         extracts for dashboards
```

## Principles

- Raw files are never edited. Every load checks the checksum first.
- Every number in a report must be reproducible from code.
- Loads fail loudly. A bad value stops the build rather than being dropped.
