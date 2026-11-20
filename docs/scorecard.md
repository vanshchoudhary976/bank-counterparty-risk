# Week 3: bank failure scorecard (Module B)

Illustrative only. This is a learning project built on public FDIC data. It is not a regulatory model, and nothing here claims compliance with any regulatory standard.

## What it does

The scorecard ranks US banks by their risk of failing within the next four quarters, using three ratios from the FDIC call reports: equity to assets, loans to deposits and annualised return on assets.

## Steps, in plain language

1. **Label.** A bank-quarter is 1 if the bank fails within 12 months after its report date, otherwise 0.
2. **Clean the panel.** Only quarter-end dates are kept. A bank-quarter is dropped if the bank had already failed, or if the data ends less than 12 months later, because we cannot yet see whether it would fail.
3. **Split by time.** The model trains on earlier report years and is tested on later ones. A random split would let the model learn from the future.
4. **Score each ratio (weight of evidence).** Each ratio is grouped into five bins by quantile, using training data only. Missing values get their own bin. Each bin gets a score from how survivors and failures are spread across it.
5. **Measure strength (information value).** Rules of thumb: below 0.02 weak, 0.1 to 0.3 medium, above 0.3 strong.
6. **Fit.** Logistic regression on the scores gives a probability of failure for each bank-quarter.
7. **Grade.** Ten grades are set from the training period's probabilities, so each grade holds roughly the same number of training banks. Grade 1 is the safest, grade 10 the riskiest. Repeated cut-offs leave some grades empty, which the report shows.
8. **Check.** The out-of-time AUC measures ranking power (0.5 is chance, 1.0 is perfect). The grade table shows failure rates per grade on the test set.

## Results (first full run on the FDIC warehouse)

- Training period: 1,323,217 bank-quarters, 11,678 labelled failures.
- Test period (report years 2011 onward): 336,383 bank-quarters, 652 labelled failures.
- Out-of-time AUC: 0.963.
- Information value: equity to assets 2.94, annualised ROA 2.88, loans to deposits 0.04. The two strong ratios are very high, which fits failing banks having very thin equity and weak earnings in the year before failure. The data checks found no missing or zero values in that window that could explain it, except seven zero-equity quarters.
- Grade 10 holds 11,021 test bank-quarters, about 3.3% of the test set. It contains 581 of the 652 failures (about 89%), with a failure rate of 5.27%, against 0.10% in grade 9.

## Limits

- **The model is a screen, not a precise ranking.** Its strength is flagging the riskiest group. Grades 1 to 9 hold between 0 and 16 failures each in the test set, so their failure rates cannot be reliably ordered. Some grades show small reversals (for example grade 2 at 0.00% against grade 1 at 0.01%). Those differences are one or two banks.
- **Few failures overall.** Only 652 failures fall in the test period, and most come from a small number of banks. Results will move with a different test window.
- **Small input set.** Only three ratios are used. Adding more would be the next step if the out-of-time results needed it.
- **Some banks are not matched.** Failures before deposit insurance have no certificate number, so they cannot be linked to a bank and are excluded.
- **Training period differs from the test period.** Failure rates are much higher in the training years. The model is trained on a different environment from the one it is tested in.

## Starting choices

- Failure horizon: four quarters.
- Ratios: equity to assets, loans to deposits, annualised ROA.
- Test period: report years 2011 onward.
