"""Rolling out-of-time check inside 2005 to 2013. The 2014 to 2022 test set is never read.

For each year Y in 2011, 2012, 2013: fit on report dates from 2005 to the end of Y-1, then score year Y.
Every fit uses the same steps as develop.py: complete rows, rule 5 caps from its own training years only,
standardisation, and the logistic model. Benchmark: the single-ratio baseline (Tier 1 leverage), fitted on
the same training years. Rows outside 2005 to 2013 are ignored by construction.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Sequence

from credit_risk.scorecard.baseline import fit_single_ratio_baseline
from credit_risk.scorecard.evaluation import auc
from credit_risk.scorecard.labels import Observation
from credit_risk.scorecard.metrics import gini, ks_statistic
from credit_risk.scorecard.model import fit_logistic
from credit_risk.scorecard.panel import RATIO_COLUMNS
from credit_risk.scorecard.split import MIN_EVENTS
from credit_risk.scorecard.standardise import Standardiser
from credit_risk.scorecard.week3 import BASELINE_RATIO, BASELINE_TARGET_SHARE
from credit_risk.scorecard.winsorise import Winsoriser

TEST_YEARS = (2011, 2012, 2013)
TRAIN_START = date(2005, 1, 1)
RESULTS_NAME = "rolling_results.txt"


@dataclass(frozen=True)
class YearResult:
    year: int
    train_rows: int
    train_events: int
    test_rows: int
    test_events: int
    model_auc: float
    model_gini: float
    model_ks: float
    baseline_auc: float


def _complete(rows: Sequence[Observation]) -> list[Observation]:
    return [o for o in rows if all(o.features.get(n) is not None for n in RATIO_COLUMNS)]


def score_year(observations: Sequence[Observation], year: int) -> YearResult:
    train = _complete([o for o in observations if TRAIN_START <= o.report_date <= date(year - 1, 12, 31)])
    test = _complete([o for o in observations if date(year, 1, 1) <= o.report_date <= date(year, 12, 31)])
    if not train or not test:
        raise ValueError(f"year {year}: training or test rows are empty after dropping incomplete rows")
    train_events = sum(o.label for o in train)
    test_events = sum(o.label for o in test)
    if train_events < MIN_EVENTS:
        raise ValueError(f"year {year}: training has {train_events} failures; need at least {MIN_EVENTS}")
    if test_events == 0 or test_events == len(test):
        raise ValueError(f"year {year}: the test year needs both failures and survivors")

    names = list(RATIO_COLUMNS)
    winsoriser = Winsoriser(names).fit([o.features for o in train])
    train_w = [winsoriser.transform(o.features) for o in train]
    test_w = [winsoriser.transform(o.features) for o in test]
    std = Standardiser(names).fit(train_w)
    model = fit_logistic([std.transform(f) for f in train_w], [o.label for o in train], names, C=1.0)
    labels = [o.label for o in test]
    scores = [model.predict_pd(std.transform(f)) for f in test_w]

    baseline = fit_single_ratio_baseline(train_w, BASELINE_RATIO, BASELINE_TARGET_SHARE)
    base_scores = [baseline.risk_score(f) for f in test_w]

    return YearResult(
        year=year,
        train_rows=len(train),
        train_events=train_events,
        test_rows=len(test),
        test_events=test_events,
        model_auc=auc(scores, labels),
        model_gini=gini(scores, labels),
        model_ks=ks_statistic(scores, labels),
        baseline_auc=auc(base_scores, labels),
    )


def run_rolling(observations: Sequence[Observation]) -> list[YearResult]:
    return [score_year(observations, year) for year in TEST_YEARS]


def format_rolling(results: Sequence[YearResult]) -> str:
    lines = ["Rolling out-of-time check, 2011 to 2013. Each year is scored by a model fitted only on earlier years.",
             "The 2014 to 2022 test set is not read.", ""]
    lines.append("  year  train rows  train failures  test rows  test failures  model AUC  model Gini  model KS  baseline AUC")
    for r in results:
        lines.append(f"  {r.year}  {r.train_rows:>10}  {r.train_events:>14}  {r.test_rows:>9}  {r.test_events:>13}"
                     f"  {r.model_auc:>9.3f}  {r.model_gini:>10.3f}  {r.model_ks:>8.3f}  {r.baseline_auc:>12.3f}")
    model = [r.model_auc for r in results]
    base = [r.baseline_auc for r in results]
    lines += ["", f"Model AUC range: {min(model):.3f} to {max(model):.3f}; "
                  f"baseline AUC range: {min(base):.3f} to {max(base):.3f}",
              "Limitations: each test year has a small number of failures, so a single year is noisy.",
              "The result is an out-of-time check inside 2005 to 2013, not the blueprint test gate, which is recorded as not met."]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    import duckdb

    from credit_risk.config import ProjectPaths
    from credit_risk.scorecard.labels import build_observations
    from credit_risk.scorecard.panel import load_panel

    paths = ProjectPaths.default()
    if not paths.warehouse_file.exists():
        print(f"Warehouse not found at {paths.warehouse_file}. Run make load first.")
        return 1
    con = duckdb.connect(str(paths.warehouse_file), read_only=True)
    try:
        panel, failures = load_panel(con, view="clean_scorecard_inputs")
    finally:
        con.close()
    data_end = max(report_date for _, report_date, _ in panel)
    observations = build_observations(panel, failures, data_end=data_end)
    text = format_rolling(run_rolling(observations))
    reports = paths.root / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    (reports / RESULTS_NAME).write_text(f"Run {datetime.now().isoformat(timespec='seconds')}\n{text}\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
