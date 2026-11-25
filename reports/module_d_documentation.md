# Module D: stress testing and early-warning system

**Status: ILLUSTRATIVE.** Shocks, thresholds and the back-test are as documented below. Nothing here is a regulatory stress test or a production warning system.

## 1. Purpose and scope

Module D asks two questions: what happens to each counterparty's grade, probability of default and limit if conditions turn bad, and would simple warning rules have flagged the banks that failed, and how often would they have flagged banks that survived?

## 2. Stress scenarios (step 1)

Balance sheets at 2022 Q4 for the 12 illustrative counterparties. Each scenario changes the balance sheet by a stated rule, recomputes the six scorecard ratios, and re-scores the bank with the Week 4 model.

| Scenario | Shock | Assumptions |
|---|---|---|
| Deposit run | Deposits fall 15% at once | Securities sold to meet outflows, sale loss 3% of the outflow |
| Credit shock | Provisions of 3% of net loans | Proxy for non-current loans, which are not loaded |
| Rate shock | Rates up 200 basis points | Securities 25% of assets, duration 4 years; loss goes to equity |
| Combined | Half of each shock | Deposit run 7.5%, provisions 1.5%, rates up 100 basis points |

Assumptions are in `src/credit_risk/stress/scenarios.py`. The credit shock is a proxy and drives most of the result: it moves nine of 12 banks to grade 10 (reduce-only). Its size is a stated sensitivity, not a finding about the real banks.

### 2.1 Results

- Credit shock is the most severe scenario. Nine of 12 banks move to grade 10.
- Combined scenario: SouthState Bank moves from grade 4 to grade 9 and from 47% to 116% of its limit. It is the only breach in the scenarios.
- Rate shock: Tier 1 leverage falls by about 2 points for most banks. Limit utilisation rises for Wells Fargo (6% to 15%) and Arrow Bank (6% to 16%), but no bank crosses 100%.
- Deposit run: small effects. Largest grade change is Arrow Bank (6 to 7).
- Rosedale Bank and Centreville Bank barely move, except under the credit shock.

Exposure is held at the current peak PFE in this step. Exposure changes under stress are not modelled yet.

## 3. Early-warning rules (step 2)

Rules and thresholds are in `src/credit_risk/warning/rules.py`, fixed before the back-test.

| Rule | Amber | Red |
|---|---|---|
| Tier 1 leverage | Below peer 25th percentile (same quarter) | Below 6% |
| Loans to deposits | Above peer 75th percentile | Above 100% and rising four quarters |
| Rating grade | Downgrade of one notch in a quarter | Downgrade of two notches, or grade 8 and worse |
| Asset growth | Above 25% a year | Above 40% with falling Tier 1 |

Not run: non-current loans and securities unrealised losses, because those fields are not loaded.

Justification for the thresholds is in the code. The grade 8 threshold was justified as "the bottom three grades", which was wrong: those grades hold about a fifth to a third of all bank-quarters, so the trigger fires far more often than intended. That error is recorded here, not corrected.

### 3.1 Back-test results

| Window | Failures | Failures flagged red at least 4 quarters ahead | Survivors with any red flag (any quarter in window) | Quarter false alarm rate |
|---|---|---|---|---|
| 2008 to 2012 | 474 | 84% | 66% of 8,041 survivors | 29.1% of 149,421 survivor bank-quarters |
| 2023 cases | 5 | 20% | 39% of 4,755 survivors | 19.4% of 37,034 survivor bank-quarters |

The 84% hit rate is computed over all red flags at any time before failure, so an early flag counts even if it came many quarters ahead. The survivor "any red" rate covers the whole window, which is why it is high. The quarter-level false alarm rate is the fairer measure.

### 3.2 Diagnosis

Almost all survivor false alarms come from the grade rule:

- 2008 to 2012: the grade rule fires on 27.7% of survivor bank-quarters. The other rules fire on 0.2% to 2.2% each.
- 2023 cases: the grade rule fires on 18.1% of survivor bank-quarters.
- The same rule also produces most of the early warnings for failing banks (3,589 pre-failure red quarters, against 1,894 for the Tier 1 floor).

So the grade rule separates failing banks from healthy ones only weakly, and it is too loose by design.

## 4. Checklist (blueprint Module D)

| Check | Result |
|---|---|
| Stress scenarios: deposit run, credit shock, rate shock, combined | Done (section 2). Assumptions in code |
| Stressed rating, PD and limit utilisation for each counterparty | Done (section 2.1). Exposure change not done |
| Expected loss change under stress | Not done. Planned for the next step |
| Assumptions recorded in config/scenarios.yaml | Partly. Assumptions are in Python code and the report, not a YAML file |
| Early-warning rules, transparent and justified | Done (section 3). Two rules not run (data not loaded) |
| Thresholds fixed before the back-test | Done. Thresholds were not changed after the result |
| Back-test on 2008 to 2012 failures and survivors | Done (section 3.1) |
| Back-test on 2023 cases | Done, but only 5 failures. Too few to judge |
| Misses explained | Done (section 3.2) for the grade rule |
| Tableau dashboard | Not done |

## 5. Gate status

- Week 6 gate ("back-test misses explained, thresholds frozen"): NOT MET for the early-warning system. The back-test is run and its misses explained, but the false alarm rate (29% by quarter) is too high to call the system credible.
- Stress testing: the scenarios run and the results are reported. Expected loss change and the exposure change are not done.

## 6. Limitations

- Shocks, the credit proxy, the securities share and duration, and the sale loss rate are assumptions, not data.
- Grades come from a scorecard fitted on 2005 to 2010, so the 2008 to 2010 back-test is in-sample.
- The 2023 window has 5 failures. It cannot support a conclusion.
- Peer percentiles are taken across all banks in the same quarter, not within a peer group.
- The grade 8 rule was set too loosely. Any corrected rule would need a fresh test window, and the data we have does not provide one.
- Two of the blueprint's early-warning rules are not run, because non-current loans and securities unrealised losses are not loaded.

## 7. Reproduce

    python -m credit_risk.stress.run_stress
    python -m credit_risk.warning.run_warning
    python -m credit_risk.warning.diagnose
    make test
