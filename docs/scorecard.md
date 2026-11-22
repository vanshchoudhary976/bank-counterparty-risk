# Week 3: Bank rating scorecard (illustrative)

Status: Week 3 results on the blueprint split. Test years not scored.
All exposures and ratings in this project are illustrative. Nothing here is a regulatory rating or a compliance statement.

## What was built

- A bank-quarter panel from public FDIC call report data, with failures taken from the FDIC failure list.
- Event definition: a bank is an event in a quarter if it fails within the next four quarters (12-month horizon).
- Time-based split, fixed before any modelling:
  - Development: 2005 to 2010
  - Validation: 2011 to 2013
  - Out-of-time test: 2014 to 2022, not scored in Week 3
  - Case study (later weeks): 2022 Q4 to 2023 Q1 (Silicon Valley Bank, Signature, First Republic)
- Two benchmarks, both measured on validation:
  1. A single-ratio baseline: Tier 1 leverage, with its threshold set on development data only.
  2. An expert CAMELS score: six ratios, percentile-ranked against development, with weights set before results.

## Results (validation, 2011 to 2013)

| Set | Years | Bank-quarters | Events |
|---|---|---|---|
| Development | 2005 to 2010 | 204,230 | 1,580 |
| Validation | 2011 to 2013 | 87,196 | 477 |
| Test (not scored) | 2014 to 2022 | 203,030 | 153 |

- Single-ratio baseline (Tier 1 leverage, threshold 7.39%): flags 7.9% of validation banks. Validation AUC 0.991.
- Expert CAMELS score: validation AUC 0.879.

AUC is the share of failing bank-quarters that the score ranks above surviving ones (1.0 is perfect, 0.5 is random).

## Limits and disclosures

1. The test split was first set at 2019. After looking at results, it was moved to 2011. This was a choice made after seeing data, and it is disclosed here. Future decisions must not change split dates after results are seen.
2. The single-ratio baseline reaches a validation AUC of 0.991. That is high enough to need checking before it is used as the benchmark for the scorecard. The Week 4 work will check whether the ratio is already distorted in the quarters just before failure, and whether it mainly catches the largest failures.
3. The expert score is a transparent benchmark, not a fitted model. Its weights are illustrative (capital 30%, asset quality 25%, earnings 15%, liquidity 20%, efficiency 10%).
4. The FDIC financials for three ratios (RBC1AAJ, LNLSRES, EEFFR) are loaded, but their units were confirmed against the definitions file and a spot check only. Treat them as provisional until the Week 4 check is done.
5. Nothing here is validated for regulatory, IFRS 9 or internal-rating use.

## Reproduce

    make load
    python -m credit_risk.scorecard.week3

Tests: `make test` (155 passing at this stage).
