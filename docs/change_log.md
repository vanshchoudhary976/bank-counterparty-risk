# Change log: Project F bank counterparty scorecard

Every change to the rules, data, model or test design is recorded here, with the date, the reason, and whether
it was made before or after the results it responds to. Nothing is removed from this log.

## Freeze

From 22 November 2026 the cleaning rules (1 to 6), the caps (rule 5), the model specification (six inputs,
logistic regression, C = 1.0, standardised after winsorising) and the evaluation design (rolling out-of-time
check, 2011 to 2013) are frozen for this version. Results are reported as they are. Any later change starts a
new version and a new entry.

## Entries

| Date | Change | Reason | Made before or after seeing results |
|---|---|---|---|
| 2026-11-22 | Week 4 run on the original pipeline: test set (2014 to 2022 Q3) scored once | Blueprint Module B step | Before (first results) |
| 2026-11-22 | Raw FDIC fields checked for extreme rows (units by year, denominators, source records) | Week 4 result showed a sign mismatch, unstable coefficients and collapsed grades | After the test result |
| 2026-11-22 | Cleaning rules 1 to 4: drop zero deposits and zero loans; drop equity above assets; keep negative equity; treat exact zero efficiency as missing | Raw check showed these rows are reported that way by the source | After the test result |
| 2026-11-22 | Cleaning rule 6: drop Tier 1 above 50% or equity above half of assets | Rule 5 percentile check showed the 99th percentile set by implausible capital values | After the test result |
| 2026-11-22 | Rule 5: winsorise each input at development 1st and 99th percentiles | Extreme values stretched the spread of each input | After the test result |
| 2026-11-22 | Proposed test window 2023 Q2 to 2025 Q2 | Test set 2014 to 2022 already used | After the test result |
| 2026-11-22 | Proposed window rejected: only 8 failures in its 12-month horizons | Blueprint needs about 100 training events; a test needs enough failures to be meaningful | After the count |
| 2026-11-22 | Blueprint test gate recorded as NOT MET. Replaced by a rolling out-of-time check inside 2011 to 2013 | No test window with enough failures exists in the current data | After the count |
| 2026-11-22 | Grade cut-offs computed from development PDs, not validation PDs (bug fix in develop.py) | The first version built cut-offs from validation PDs, so the validation grade table was not out of sample | Before rerunning the grade review; the fix uses only development data |

## Gate status

- Blueprint Module B gate ("test set used once, limitations section written"): the test set was used once (2014 to 2022 Q3) on the original pipeline, and the result failed. The gate is recorded as not met for this version.
- Substitute check: rolling out-of-time check on 2011, 2012 and 2013 (reports/rolling_results.txt). It is weaker than the blueprint test, because it reuses data already seen during development.
