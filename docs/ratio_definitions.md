# Ratio definitions

Every ratio used in this project, with its formula, source field and units.
All figures are illustrative analysis of public FDIC data. Nothing here is a regulatory calculation.

## Units and basics

- Amounts from FDIC financials (TOTAL_ASSETS, EQTOT, LNLSNET, DEP, NETINC) are in thousands of USD.
- Ratios are stored as decimals: 0.10 means 10%.
- Each row is one bank (CERT) at one quarter end (REPDTE). Quarter ends only.
- Missing inputs give a missing ratio, never zero. A zero denominator also gives a missing ratio.

## Ratios used in the scorecard and analysis

| Ratio | Formula | FDIC source field(s) | Notes |
|---|---|---|---|
| Equity to assets | total equity / total assets | EQTOT / ASSET | Simple capital measure. Used in peer analysis. |
| Loans to deposits | net loans / total deposits | LNLSNET / DEP | Above 1.0 means loans exceed deposits. |
| ROA, year to date | net income / total assets | NETINC / ASSET | NETINC is calendar year to date, so a June report covers six months. Not comparable across quarters without annualising. |
| ROA, annualised | (12 / month of report date) x net income / total assets | NETINC / ASSET | June multiplies by 2, December by 1. An estimate for a part-year. |
| Tier 1 leverage | Tier 1 leverage ratio from the FDIC field, stored as a percent and divided by 100 | RBC1AAJ | Used as the single-ratio baseline. Units confirmed against the definitions file only; still provisional until the Week 4 check. |
| Allowance to loans | allowance for loan and lease losses / (net loans + allowance) | LNLSRES, LNLSNET | Uses gross loans as the denominator, so the figure is never inflated by a small loan book. |
| Efficiency ratio | efficiency ratio from the FDIC field, stored as a percent and divided by 100 | EEFFR | Lower is better. Units provisional, as above. |

## Expert CAMELS score inputs

The expert score uses these six ratios with fixed weights, set before any results were seen:

| Ratio | Higher means | Weight |
|---|---|---|
| Tier 1 leverage | safer | 15% |
| Equity to assets | safer | 15% |
| Allowance to loans | riskier | 25% |
| ROA, annualised | safer | 15% |
| Loans to deposits | riskier | 20% |
| Efficiency ratio | riskier | 10% |

Each ratio is turned into a percentile against the development set (2005 to 2010), so 1.0 is the riskiest and 0.0 the safest.

## Failure and event definitions

- Failure: a bank on the FDIC failure list, with the failure date.
- Event (12-month horizon): a bank-quarter is an event if the bank fails within the following four quarters.
- Failures with no CERT (488 of 4,117) cannot be linked to a bank and are left out of bank-level analysis. They are counted for information only.

## Size bands (peer groups)

Set by total assets at each quarter end, in USD:

- a: under $1bn
- b: $1bn to $10bn
- c: $10bn to $100bn
- d: over $100bn

A bank can move between bands as it grows or shrinks. Bands are for comparing like with like. They are not regulatory categories.

## Open items

- Tier 1 leverage and efficiency ratio units are provisional until confirmed on raw data (Week 4 check).
- The 2026 data is June only, so 2026 figures are part-year.
