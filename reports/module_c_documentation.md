# Module C: illustrative counterparty exposure and limits

**Status: ILLUSTRATIVE.** The trades, the capital base, the wrong-way factor and the loss-given-default are invented. The counterparties are real banks, graded by the Week 4 scorecard. Nothing here is a regulatory, IFRS 9 or production output.

## 1. Purpose and scope

Module C asks how much a counterparty could owe us if it failed, and whether that is inside the limit we set for it. It covers: an invented portfolio, a simplified Monte Carlo of exposure, collateral with a margin period, limits by grade, concentration, wrong-way risk and expected loss.

## 2. Counterparties

- Selection: banks that are active and report in 2022 Q4 with total assets of at least $1bn (1,000,000 in the FDIC's thousands of dollars). Twelve are drawn with seed 42.
- Grades: the Week 4 scorecard (six ratios, logistic, Platt-calibrated, 10-grade master scale from development PDs). Grades are a model output. For example, Wells Fargo Bank, National Association is graded 6, which does not reflect its real credit quality. The scorecard has only six ratios.

## 3. Portfolio (invented)

- 2 to 4 trades per counterparty: interest rate swap (IRS), FX forward, repo, or deposit placed with the bank.
- Notionals: median 25,000,000 (invented), lognormal spread of 0.6.
- Maturities: 0.5 to 5 years, in quarter steps.
- Netting set: one per counterparty.
- Collateral agreement: any counterparty with an IRS or repo trade is treated as having a collateral agreement for its whole netting set.
- Direction: deposits and repos are lending of cash (the counterparty owes us). IRS and FX direction is drawn with the seed.
- Seed 42. The same seed reproduces the same portfolio and exposures exactly (tested).

## 4. Exposure simulation (simplified)

- 5,000 paths, monthly dates out to the longest maturity.
- Interest rate: Vasicek mean reversion (a = 0.10, long-run rate 3%, sigma 1%). Invented parameters.
- FX: geometric Brownian motion (sigma 10%). Invented parameter.
- Revaluation: IRS by closed-form Vasicek bonds; FX forward as notional times (spot minus strike) times the discount factor; repo and deposit as the full principal until maturity (a simplification, see Limitations).
- Exposure per netting set = max(sum of trade values, 0). PFE = 95th percentile across paths at each date. Peak PFE = maximum over dates.

## 5. Collateral and margin

- Threshold 1,000,000; minimum transfer 100,000 (invented).
- Collateral held = amount above the threshold, if it clears the minimum transfer.
- Margin period of risk: 10 days, rounded up to one monthly step (conservative).
- Collateralised exposure = exposure one step later, less collateral held at the start, floored at zero.
- Collateral never raises exposure (tested). Table in section 7.2 shows the gap with and without collateral.

## 6. Limits, status and breaches

- Limit = capital base (5,000,000,000, invented) times a grade percentage: grades 1 to 3 at 5%, grades 4 to 7 at 2.5%, grades 8 to 9 at 1%, grade 10 at 0% (reduce-only).
- Utilisation = collateralised, post-margin peak PFE divided by the limit.
- Status: green below 80%, amber from 80% to 100%, red above 100%. A grade 10 counterparty with positive exposure is red (reduce-only).
- Breach report names the counterparty, the two trades with the largest standalone exposure, and a suggested action.

## 7. Results (from the run on 22 November 2026, seed 42)

### 7.1 Limits

All 12 counterparties are green at base. Highest utilisation: SouthState Bank at 47%. This result depends on the invented capital base; it says nothing about the real banks' capacity.

### 7.2 Collateral gap

Collateral reduces peak PFE for most counterparties. Largest reduction: Arrow Bank, from about 122m to about 8m. Reason: its netting set includes repo or an IRS, so the collateral agreement applies to the whole set. Two counterparties show no gap (First National Bank Texas and SouthState Bank) because their netting sets have no collateral agreement: they hold no IRS or repo trades.

### 7.3 Concentration

- Top-5 share of peak collateralised PFE: 88%.
- Herfindahl-Hirschman index: 3,033 (10,000 means one counterparty).
- Not done: by bank business model and by country. These fields are not loaded.

### 7.4 Wrong-way risk

Scenario: post-margin exposure multiplied by 1.5 where repo is present, and the counterparty downgraded by two grades (limit falls with the new grade). Assumption: repo collateral is the counterparty's own securities, so it loses value as the counterparty weakens.

- Two counterparties turn red because the downgrade takes them to grade 10 (reduce-only): First National Bank Texas (grade 8 to 10) and North State Bank (grade 8 to 10).
- Other counterparties stay green after the downgrade. Largest utilisation after the downgrade: Arrow Bank at 24%.

### 7.5 Expected loss

EL = EAD x PD x LGD, with:
- EAD: collateralised peak PFE (a simplification of EAD).
- PD: observed validation failure rate by grade from the Week 4 grade table, floored at 0.05%. The floor applies to every grade except 10 (the observed rate is 6.7%). No counterparty in this run is in grade 10.
- LGD: 45% base; sensitivity at 25% and 60%.

Total expected loss: about 25,900 at 45% LGD (14,400 at 25%, 34,500 at 60%). Small values follow from the invented notionals and the PD floor.

## 8. Checklist (blueprint Module C)

| Check | Result |
|---|---|
| Illustrative portfolio, labelled and seeded | Done (section 3); CSV rejects unlabelled rows |
| Exposure simulation, 5,000 paths, EPE and PFE | Done (section 4); simplified and labelled |
| Collateral and margin period of risk | Done (section 5); table in 7.2 |
| Limits as code, status bands, breach report | Done (section 6) |
| Concentration: top-5 and HHI | Done (7.3) |
| Concentration by business model and country | Not done: fields not loaded |
| Wrong-way risk scenario | Done (7.4); factor is an assumption |
| Expected loss with LGD sensitivity | Done (7.5); PD floor is an assumption |
| Acceptance: netting reduces exposure | Test passes |
| Acceptance: collateral never raises exposure | Test passes |
| Acceptance: utilisation breaches flag correctly | Test passes |
| Acceptance: results repeat exactly with the same seed | Test passes |
| Full suite | 287 passed (run on your machine, 22 November 2026) |

## 9. Gate status

- Week 5 gate ("netting, collateral and seed tests pass"): MET. The tests pass on your machine.

## 10. Limitations

- Trades, capital base, volatilities, margin terms, wrong-way factor and LGD are invented. Results show how the code behaves, not how the banks behave.
- The simulation is simplified: Vasicek and GBM, closed-form revaluation, one rate and one FX factor, no correlation between counterparties.
- Repo and deposit exposure is the full principal until maturity. Real repo exposure depends on the collateral and haircut, which are not modelled.
- Collateral applies to a whole netting set once any trade in it is collateralised. A real agreement can cover only some trades.
- Concentration by business model and by country is not done.
- The PD floor of 0.05% dominates expected loss for most grades. No grade in this run has an observed rate above zero except 5, 6, 8, 9 and 10.
- The scorecard grades are model outputs with six ratios. Some grades look wrong against the bank's real standing (see section 2).
- The wrong-way scenario changes grade and exposure together by assumption. It does not estimate how the exposure would actually move.

## 11. Reproduce

    python -m credit_risk.exposure.counterparties
    python -m credit_risk.exposure.run_exposure
    python -m credit_risk.exposure.limits
    python -m credit_risk.exposure.measures
    make test
