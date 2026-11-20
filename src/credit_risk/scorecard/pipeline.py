"""Run the whole Week 3 scorecard: labels, out-of-time split, WoE, model, PD, grades, checks.

Command line (from the project folder, with the warehouse built):
    python -m credit_risk.scorecard.pipeline --test-from-year 2021

Illustrative only. The output is a learning exercise on public FDIC data, not a regulatory model.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Sequence

from credit_risk.config import ProjectPaths
from credit_risk.scorecard.evaluation import GradeRow, auc, default_rate_by_grade, is_risk_ordered
from credit_risk.scorecard.labels import Observation, build_observations, out_of_time_split
from credit_risk.scorecard.model import FittedModel, fit_logistic
from credit_risk.scorecard.panel import RATIO_COLUMNS, load_panel
from credit_risk.scorecard.scale import MasterScale, training_quantile_cutoffs
from credit_risk.scorecard.woe import WoeTable, build_woe_table, quantile_cuts

BINS_PER_RATIO = 5


@dataclass(frozen=True)
class ScorecardResult:
    train_rows: int
    train_failures: int
    test_rows: int
    test_failures: int
    woe_tables: dict[str, WoeTable]
    model: FittedModel
    test_auc: float
    cutoffs: tuple[float, ...]
    grade_rows: list[GradeRow]
    grades_risk_ordered: bool


def run_scorecard(
    observations: Sequence[Observation],
    test_from_year: int,
    cutoffs: Sequence[float] | None = None,
) -> ScorecardResult:
    """Fit on earlier years, score later years, and check the ranking and the grades.

    If cutoffs is None, the grade cut-offs are set from training-period probabilities only.
    """
    split = out_of_time_split(list(observations), test_from_year)
    features = RATIO_COLUMNS

    woe_tables: dict[str, WoeTable] = {}
    for name in features:
        train_values = [o.features.get(name) for o in split.train]
        train_labels = [o.label for o in split.train]
        cuts = quantile_cuts(train_values, BINS_PER_RATIO)
        woe_tables[name] = build_woe_table(train_values, train_labels, cuts)

    def woe_row(observation: Observation) -> list[float]:
        return [woe_tables[name].woe_for(observation.features.get(name)) for name in features]

    train_x = [woe_row(o) for o in split.train]
    train_y = [o.label for o in split.train]
    model = fit_logistic(train_x, train_y, feature_names=features, C=1.0)

    train_pd = [model.predict_pd(woe_row(o)) for o in split.train]
    test_pd = [model.predict_pd(woe_row(o)) for o in split.test]
    test_y = [o.label for o in split.test]
    test_auc = auc(test_pd, test_y)

    chosen_cutoffs = tuple(cutoffs) if cutoffs is not None else training_quantile_cutoffs(train_pd)
    scale = MasterScale(chosen_cutoffs)
    grades = [scale.grade(p) for p in test_pd]
    grade_rows = default_rate_by_grade(grades, test_y)

    return ScorecardResult(
        train_rows=len(split.train),
        train_failures=sum(train_y),
        test_rows=len(split.test),
        test_failures=sum(test_y),
        woe_tables=woe_tables,
        model=model,
        test_auc=test_auc,
        cutoffs=chosen_cutoffs,
        grade_rows=grade_rows,
        grades_risk_ordered=is_risk_ordered(grade_rows),
    )


def format_report(result: ScorecardResult) -> str:
    lines = [
        "Week 3 scorecard (illustrative, public FDIC data)",
        f"Train: {result.train_rows} bank-quarters, {result.train_failures} labelled failures",
        f"Test (out-of-time): {result.test_rows} bank-quarters, {result.test_failures} labelled failures",
        "",
        "Information value by ratio (rule of thumb: 0.02 weak, 0.1 to 0.3 medium, above 0.3 strong):",
    ]
    for name, table in result.woe_tables.items():
        lines.append(f"  {name}: IV = {table.information_value:.3f}")
    lines += ["", "Logistic regression coefficients (negative = higher WoE means lower failure risk):"]
    lines.append(f"  intercept = {result.model.intercept:.3f}")
    for name, coef in zip(result.model.feature_names, result.model.coefficients):
        lines.append(f"  {name} = {coef:.3f}")
    lines += ["", f"Out-of-time AUC: {result.test_auc:.3f} (0.5 is chance, 1.0 is perfect)"]
    lines.append("Grade cut-offs (PD upper limits, set from training banks only): " + ", ".join(f"{c:.4%}" for c in result.cutoffs))
    lines += ["", "Grades on test set:"]
    lines.append("  grade  banks  failures  failure rate")
    for row in result.grade_rows:
        lines.append(f"  {row.grade:>5}  {row.count:>5}  {row.failures:>8}  {row.failure_rate:>11.2%}")
    lines.append("")
    verdict = "yes" if result.grades_risk_ordered else "no, review the cut-offs and the bins"
    lines.append(f"Failure rates rise with grade: {verdict}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    import duckdb

    parser = argparse.ArgumentParser(description="Run the Week 3 bank failure scorecard.")
    parser.add_argument("--test-from-year", type=int, required=True, help="first report year in the test set")
    parser.add_argument("--warehouse", type=Path, default=ProjectPaths.default().warehouse_file)
    args = parser.parse_args(argv)

    if not args.warehouse.exists():
        print(f"Warehouse not found at {args.warehouse}. Run make load first.")
        return 1

    con = duckdb.connect(str(args.warehouse), read_only=True)
    try:
        panel, failures = load_panel(con)
    finally:
        con.close()
    if not panel:
        print("The ratio view is empty. Check that sql/03_ratios.sql has been applied.")
        return 1

    data_end: date = max(report_date for _, report_date, _ in panel)
    observations = build_observations(panel, failures, data_end=data_end)
    result = run_scorecard(observations, test_from_year=args.test_from_year)
    print(format_report(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
