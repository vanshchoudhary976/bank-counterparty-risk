# Credit Committee Memo 2: JPMorgan Chase Bank, National Association (ILLUSTRATIVE)

**Counterparty:** JPMorgan Chase Bank, National Association (FDIC cert 628)
**Data date:** 30 June 2026 (latest quarter in the warehouse at the time of writing)
**Request:** New counterparty limit for the illustrative portfolio
**Prepared by:** Vansh Choudhary (illustrative exercise, not a real credit decision)

## Recommendation

Approve a new illustrative counterparty limit of $50m, subject to quarterly monitoring against the triggers below. The bank's capital, funding and earnings ratios are all stable across the last four quarters, and none of the monitored ratios is close to its trigger level.

## Counterparty overview

JPMorgan Chase Bank, National Association reported total assets of about $4.09 trillion at 30 June 2026, up from about $3.81 trillion at 30 September 2025. Total equity was about $341.6bn at the same date. The bank is one of the largest deposit takers in the United States, so its size is a material part of why the exposure is considered low-risk here.

The warehouse also holds a second record under the JPMorgan name (cert 21761, roughly $71m of total assets). It is a different, much smaller entity and has been excluded from this memo.

## Financial analysis

| Date | Total assets ($k) | Total equity ($k) | Net loans ($k) | Equity to assets | Loans to deposits | Net income YTD ($k) |
|---|---|---|---|---|---|---|
| 30 Sep 2025 | 3,813,431,000 | 331,986,000 | 1,433,072,000 | 8.71% | 54.1% | 38,227,000 |
| 31 Dec 2025 | 3,752,662,000 | 335,970,000 | 1,471,951,000 | 8.95% | 54.6% | 49,644,000 |
| 31 Mar 2026 | 4,016,571,000 | 335,961,000 | 1,493,977,000 | 8.36% | 53.6% | 13,974,000 |
| 30 Jun 2026 | 4,091,315,000 | 341,610,000 | 1,535,635,000 | 8.35% | 54.4% | 31,335,000 |

- Equity to assets stayed between 8.4% and 9.0% across the four quarters. It is lower than the smaller banks in the earlier memos, which is expected for a bank of this size.
- Loans to deposits stayed between 53.6% and 54.6%. The bank is not dependent on wholesale funding to lend.
- Net income is reported year to date, so the 2026 figures cover six months. The annualised return on assets at 30 June 2026 is about 1.5%.
- Total assets rose by about 7% between September 2025 and June 2026, with net loans rising by about 7% over the same period.

## Internal rating

No internal grade is held for this bank in the warehouse. The Module D early-warning score was not run for this bank in the current build, so this memo does not state a grade. A grade should be assigned before any limit is used.

## Key risks

- **Scale and concentration.** A large part of the illustrative portfolio's exposure would sit with one institution, so an event at the bank would affect many other positions at once.
- **Market and trading risk.** The warehouse holds no data on trading book losses, securities losses or derivatives exposure, so these risks cannot be measured here.
- **Equity buffer relative to size.** Equity is about 8.4% of assets. This leaves less room to absorb losses than a 12% to 13% ratio would give, although it is still well above the levels seen at the failed banks in the earlier memo.

## Mitigants

- Loans to deposits near 54% means the bank holds a large amount of deposits relative to its loans.
- Earnings are positive in every quarter shown, and year-to-date income is well above zero.
- The bank's ratios moved within a narrow range over the period, with no sudden deterioration.

## Exposure and limit

The proposed limit is $50m. This is a placeholder for the illustrative portfolio and is not derived from the portfolio's capital, which is not in the data. The figure should be revisited once the portfolio's capital and concentration rules are set.

## Stress results

Module D stress tests were not run for this bank, so no stressed grade or expected loss is given. This is a gap in the analysis and should be closed before the limit is used in practice.

## Monitoring triggers

- Equity to assets below 7.5%.
- Loans to deposits above 65%.
- Annualised return on assets below 0.5%.
- Any quarter where net income year to date falls below the prior-quarter figure by more than 25%.

## Conclusion

The bank's data shows stable capital, funding and earnings across the last four quarters. The proposed $50m limit is approved for the illustrative portfolio, subject to the triggers above and to closing the stress-test and rating gaps before any real use.

---

**Data notes**

- Figures were read from a screenshot of the warehouse query output (bank_ratios, cert 628, latest eight quarters). Re-run the query and check each figure against the warehouse before committing.
- Units are assumed to be thousands of US dollars, consistent with the earlier memos. The total assets scale ($4.09 trillion) is consistent with JPMorgan's known size.
- Return on assets is taken from the warehouse column and has not been reconciled to net income.
- Asset quality data (non-performing loans, charge-offs) is not in the warehouse.
