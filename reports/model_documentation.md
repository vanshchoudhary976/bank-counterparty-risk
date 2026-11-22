# Model documentation: bank counterparty early-warning scorecard (Project F)

Version status: frozen on 22 November 2026. Blueprint Module B gate: NOT MET (section 9).
This is an illustrative model built on public FDIC data. It is not an IFRS 9 or regulatory rating, and it does not claim regulatory compliance.

## 1. Purpose and scope

- Estimates the probability that a US FDIC-insured bank fails within 12 months, from quarterly call-report ratios.
- Intended use: learning and early-warning discussion. Not a credit decision or a capital calculation.

## 2. Data

- Source: FDIC BankFind financials and failures (public), loaded into a DuckDB warehouse. 1,682,738 financial records and 4,117 failures.
- Unit of observation: one bank at one quarter-end report date.
- Inputs: six ratios, defined in `docs/ratio_definitions.md`: equity to assets, Tier 1 leverage, allowance to loans, annualised ROA, loans to deposits, efficiency ratio.
- Open data items: units of Tier 1 leverage and efficiency ratio are checked by the raw-field check. The source itself reports some zero and impossible values, handled by the cleaning rules in section 5.
- Latest report date in the warehouse: June 2026. The 2026 data is June only.

## 3. Sample windows

| Window | Report dates | Use | Status |
|---|---|---|---|
| Development | 2005 to 2010 | Fit the model | Used |
| Validation | 2011 to 2013 | Calibration, master scale, rolling check | Used |
| Original out-of-time test | 2014 to 2022 Q3 | Scored once, on the original pipeline | Used. Result failed (section 7.3) |
| Case study | 2022 Q4 to 2023 Q1 | Not scored in this version | Not done |
| Proposed fresh test | 2023 Q2 to 2025 Q2 | Rejected | Only 8 failures in the 12-month horizons. Too few to test |

## 4. Event definition and labels

- A bank-quarter is labelled 1 if the bank fails within 12 months after the report date, otherwise 0.
- Only quarter-end report dates are used. The bank must still be operating on the report date, and the full 12-month horizon must be observed.
- Counts are bank-quarters. One bank that is weak for several quarters before it fails is counted several times.

## 5. Cleaning rules (frozen)

Applied to every window from the same definitions. Counts are for development and validation together (2005 to 2013), 291,916 bank-quarters.

1. Zero deposits and zero net loans: dropped. 2,727 rows.
2. Equity above total assets: dropped. 1 row, which is also in rule 1.
3. Negative equity on an otherwise normal balance sheet: kept. 160 rows. Real distress is kept on purpose.
4. Efficiency ratio exactly 0: treated as missing. 933 rows.
6. Tier 1 leverage above 50%, or equity above half of total assets: dropped. 5,737 rows.
- Together, rules 1, 2 and 6 drop 5,926 rows (2.0%). 285,990 remain.
5. Caps: each input capped at the 1st and 99th percentiles of development data, after rules 1, 2 and 6. Caps: equity to assets 0.05204 to 0.29408; Tier 1 0.05131 to 0.30438; allowance to loans 0.00203 to 0.05080; ROA -0.05175 to 0.03075; efficiency 0.32106 to 2.09025; loans to deposits 0.23954 to 1.43053.

Why rule 6 was added: after the first caps were applied, the 99th percentile itself was set by implausible values (Tier 1 near 60%, equity near 56% of assets).

## 6. Method

1. Keep bank-quarters with all six ratios present.
2. Fit caps (rule 5) on development only, then cap development and validation.
3. Standardise on development only.
4. Fit an L2-regularised logistic regression (C = 1.0) on development.
5. Check every coefficient sign against the expected direction, and run drop-one-year sensitivity.
6. Platt calibration and the 10-grade master scale, both from validation only.
7. Benchmarks: single-ratio baseline (Tier 1 leverage, threshold at the 10% riskiest development value), and the expert CAMELS score.

## 7. Results

### 7.1 Development (2005 to 2010) and validation (2011 to 2013) refit

- Development: 198,445 bank-quarters, 1,524 failures. Validation: 85,399 bank-quarters, 463 failures.
- Coefficients (standardised, winsorised inputs): equity to assets -1.4811; Tier 1 -1.5876; allowance to loans +0.3298; ROA -0.5331; efficiency +0.2350; loans to deposits +0.6063; intercept -8.0123.
- Sign check: all six match the expected direction.
- Sensitivity: no sign flips. The largest coefficient moves are 1.87 when 2008 is dropped and 1.02 when 2010 is dropped. The estimates depend heavily on the crisis years.
- Platt calibration (validation): slope 1.1518, intercept -0.3422.
- Validation discrimination: AUC 0.990, Gini 0.981, KS 0.943.
- PSI, development to validation: allowance to loans 0.254 (above the 0.25 major-shift line); loans to deposits 0.243 (some shift); all others below 0.10.
- Master scale cut-offs (validation): 0.00000 to 0.00115. Grade counts were not reviewed in this version, so the grade distribution is not yet validated.

### 7.2 Rolling out-of-time check (2011, 2012, 2013)

Each year is scored by a model fitted only on the years before it.

| Year | Train failures | Test rows | Test failures | Model AUC | Model Gini | Model KS | Baseline AUC |
|---|---|---|---|---|---|---|---|
| 2011 | 1,524 | 29,531 | 264 | 0.990 | 0.981 | 0.947 | 0.987 |
| 2012 | 1,788 | 28,502 | 120 | 0.994 | 0.988 | 0.971 | 0.992 |
| 2013 | 1,908 | 27,366 | 79 | 0.981 | 0.963 | 0.898 | 0.980 |

- Model AUC range 0.981 to 0.994; baseline range 0.980 to 0.992.
- The model adds 0.001 to 0.003 AUC over the single-ratio baseline. Discrimination comes mainly from capital, and the six-input model adds little on top of Tier 1 leverage in these years.

### 7.3 Original out-of-time test (2014 to 2022 Q3), scored once

Run on the original pipeline, before the cleaning rules. The result is reported as it stands.

- Test: 198,264 bank-quarters, 148 failures (before dropping incomplete rows).
- AUC: model 0.962, baseline 0.961, expert score 0.830.
- Sign check: failed on efficiency ratio (coefficient -0.0017, expected positive).
- Stability: dropping 2009 moved one coefficient by 7.21.
- Master scale: grades did not order risk (grade 10 held 127 of 148 failures).
- Tier 1 standardised coefficient -8.98, which was implausible and traced to implausible capital values (section 5, rule 6).

## 8. Checklist (blueprint Module B)

| Check | Result |
|---|---|
| AUC and Gini on each set | Done: validation and rolling years in 7.1 and 7.2; original test in 7.3 |
| KS on each set | Done, same sources |
| Share of failures in riskiest decile | Not reported for the refit. Pending |
| Calibration by decile | Not reported for the refit. Pending |
| Platt calibration on validation | Done (7.1) |
| PSI development vs test, per input | Done for development vs validation (7.1). Fresh test not available |
| Coefficient signs | Done: all match (7.1). Original test failed (7.3) |
| Drop-one-year sensitivity | Done (7.1). Large moves from 2008 and 2010 |
| Benchmark vs baseline and expert | Done for the original test (7.3) and rolling years (7.2) |
| Error review of missed failures | Pending for this version |
| Master scale of 10 grades | Cut-offs done (7.1). Grade distribution not reviewed |
| One-year migration matrix | Produced in the original Week 4 run (7.3 pipeline). Not rerun |

## 9. Gate status

- Blueprint Module B gate ("test set used once, limitations section written"): NOT MET.
- The test set was used once (2014 to 2022 Q3), on the original pipeline, and the result failed. It cannot be rerun without breaking the once-only rule.
- A fresh out-of-time test with enough failures is not available in the current data. The rolling check in section 7.2 is a weaker substitute, because it reuses data already seen in development.
- Cleaning rules and caps were chosen after the 2014 to 2022 result was seen. Every change is in `docs/change_log.md`.

## 10. Limitations

- The model does not beat a single capital ratio by a meaningful margin in 2011 to 2013. Its value over Tier 1 leverage is not shown.
- Estimates depend on the crisis years (2008 to 2010). Dropping one year moves coefficients substantially.
- The allowance-to-loans input shifts between development and validation (PSI 0.254). Crisis-era reserve build-up is the likely cause.
- Counts are bank-quarters, not separate banks.
- Public FDIC data only. No supervisory information, no market data, no securities marks.
- The unrealised securities loss and uninsured deposit test on the 2023 failures is NOT done. Those fields are not loaded.
- The 2026 data is June only.
- The 12-month horizon and the event definition are design choices, not regulatory definitions.
- Grade distribution and the grade-level error review are not complete for this version.

## 11. Reproduce

- Tests: `make test`
- Load warehouse: `make load`
- Development and validation refit: `python -m credit_risk.scorecard.develop`
- Rolling out-of-time check: `python -m credit_risk.scorecard.rolling`
- Rule counts (read-only, 2005 to 2013): `python scripts/rule_counts_dev_val.py`
- The original Week 4 runner is blocked by its once-only marker and is not part of this version.
