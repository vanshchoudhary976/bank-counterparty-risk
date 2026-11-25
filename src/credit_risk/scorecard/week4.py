"""Week 4 (Module B part 2): fit, calibrate, validate, and score the out-of-time test set once.

Order, as the blueprint requires:
1. Standardise and fit the logistic model on development data only.
2. Check coefficient signs and drop-one-year sensitivity, still on development data.
3. Calibrate with Platt scaling on validation, and choose the 10-grade master scale on validation.
4. Score the out-of-time test set once, with the frozen model and scale.
5. Score the 2022 Q4 to 2023 Q1 case study with the same frozen model. Nothing is refitted.

Rows with any missing ratio are dropped before fitting. The counts dropped are reported.
The securities-loss and uninsured-deposit test needs FDIC fields that are not in the warehouse yet,
so the case study here is a grade and PD review only, and the report says so.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional, Sequence

from credit_risk.scorecard.baseline import fit_single_ratio_baseline
from credit_risk.scorecard.calibration import PlattCalibrator, fit_platt
from credit_risk.scorecard.evaluation import GradeRow, auc, default_rate_by_grade, is_risk_ordered
from credit_risk.scorecard.expert import ExpertScore
from credit_risk.scorecard.labels import Observation
from credit_risk.scorecard.metrics import (
    DecileRow,
    decile_table,
    gini,
    ks_statistic,
    psi,
    riskiest_overlap,
    share_of_failures_in_riskiest_decile,
    spearman,
)
from credit_risk.scorecard.model import fit_logistic
from credit_risk.scorecard.panel import RATIO_COLUMNS
from credit_risk.scorecard.scale import MasterScale, training_quantile_cutoffs
from credit_risk.scorecard.split import (
    SetCounts,
    blueprint_split,
    check_development_events,
    check_every_set_has_rows,
)
from credit_risk.scorecard.standardise import Standardiser
from credit_risk.scorecard.validation import (
    MissedFailure,
    YearSensitivity,
    drop_one_year_sensitivity,
    migration_matrix,
    migration_row_shares,
    missed_failures,
    sign_mismatches,
)
from credit_risk.scorecard.week3 import BASELINE_RATIO, BASELINE_TARGET_SHARE

RISKIEST_SHARE = 0.10
MISSED_SAFEST_GRADES = 3
MARKER_NAME = "week4_test_scored.marker"
RESULTS_NAME = "week4_results.txt"


@dataclass(frozen=True)
class SetMetrics:
    name: str
    auc: float
    gini: float
    ks: float


@dataclass(frozen=True)
class CaseRow:
    cert: int
    report_date: date
    pd: float
    grade: int
    label: int


@dataclass(frozen=True)
class Week4Results:
    counts: list[SetCounts]
    dropped_incomplete: dict[str, int]
    coefficients: dict[str, float]
    intercept: float
    sign_problems: list[str]
    sensitivity: list[YearSensitivity]
    calibrator: PlattCalibrator
    cutoffs: tuple[float, ...]
    validation: SetMetrics
    test: SetMetrics
    decile_validation: list[DecileRow]
    decile_test: list[DecileRow]
    riskiest_decile_share_test: float
    psi_by_input: dict[str, float]
    benchmark_auc_test: dict[str, float]
    spearman_model_expert: float
    spearman_model_baseline: float
    overlap_model_expert: float
    overlap_model_baseline: float
    grade_rows_test: list[GradeRow]
    risk_ordered_test: bool
    missed: list[MissedFailure]
    migration: list[list[int]]
    migration_stay: list[Optional[float]]
    case_study: list[CaseRow]


def _complete(rows: Sequence[Observation]) -> list[Observation]:
    return [o for o in rows if all(o.features.get(n) is not None for n in RATIO_COLUMNS)]


def _metrics(name: str, pds: Sequence[float], labels: Sequence[int]) -> SetMetrics:
    return SetMetrics(name=name, auc=auc(pds, labels), gini=gini(pds, labels), ks=ks_statistic(pds, labels))


def run_week4(observations: Sequence[Observation]) -> Week4Results:
    split = blueprint_split(list(observations))
    check_every_set_has_rows(split)
    check_development_events(split)

    raw_sets = {
        "development": split.development,
        "validation": split.validation,
        "test": split.test,
        "case study": split.case_study,
    }
    dropped = {name: len(rows) - len(_complete(rows)) for name, rows in raw_sets.items()}
    dev = _complete(split.development)
    val = _complete(split.validation)
    test = _complete(split.test)
    case = _complete(split.case_study)
    if not (dev and val and test):
        raise ValueError("after dropping incomplete rows, a modelling set is empty")

    names = list(RATIO_COLUMNS)

    # Step 1: standardise and fit on development only.
    std = Standardiser(names).fit([o.features for o in dev])
    dev_z = [std.transform(o.features) for o in dev]
    dev_y = [o.label for o in dev]
    model = fit_logistic(dev_z, dev_y, names, C=1.0)
    coefficients = dict(zip(names, model.coefficients))
    problems = sign_mismatches(coefficients)

    # Step 2: drop-one-year sensitivity, still on development only.
    def fit_coefficients(z_rows, labels):
        return dict(zip(names, fit_logistic(z_rows, labels, names, C=1.0).coefficients))

    sensitivity = drop_one_year_sensitivity(
        [(o.report_date.year, z, o.label) for o, z in zip(dev, dev_z)], names, fit_coefficients
    )

    # Step 3: calibrate and choose the grades on validation only.
    val_y = [o.label for o in val]
    val_raw = [model.predict_pd(std.transform(o.features)) for o in val]
    calibrator = fit_platt(val_raw, val_y)
    val_pd = [calibrator.calibrate(p) for p in val_raw]
    scale = MasterScale(training_quantile_cutoffs(val_pd))

    # Step 4: score the test set once, with the frozen model and scale.
    test_y = [o.label for o in test]
    test_pd = [calibrator.calibrate(model.predict_pd(std.transform(o.features))) for o in test]
    test_grades = [scale.grade(p) for p in test_pd]
    test_deciles = decile_table(test_pd, test_y)

    psi_by_input = {
        n: psi([o.features[n] for o in dev], [o.features[n] for o in test]) for n in names
    }

    # Benchmarks on the test set: the single-ratio baseline and the expert CAMELS score.
    baseline = fit_single_ratio_baseline([o.features for o in dev], BASELINE_RATIO, BASELINE_TARGET_SHARE)
    expert = ExpertScore().fit([o.features for o in dev])
    rows = []
    for o, p in zip(test, test_pd):
        base_score = baseline.risk_score(o.features)
        expert_score = expert.score(o.features)
        if base_score is not None and expert_score is not None:
            rows.append((p, base_score, expert_score, o.label))
    model_s = [r[0] for r in rows]
    base_s = [r[1] for r in rows]
    expert_s = [r[2] for r in rows]
    bench_y = [r[3] for r in rows]

    # Error review and grade check on the test set.
    missed = missed_failures(
        [(o.cert, o.report_date, p, g, o.label) for o, p, g in zip(test, test_pd, test_grades)],
        safest_grade_limit=MISSED_SAFEST_GRADES,
    )
    grade_rows = default_rate_by_grade(test_grades, test_y)

    # One-year migration, on the test set: same bank, same quarter, one year later.
    index = {(o.cert, o.report_date): g for o, g in zip(test, test_grades)}
    pairs = []
    for (cert, report_date), grade in index.items():
        try:
            later_date = date(report_date.year + 1, report_date.month, report_date.day)
        except ValueError:  # 29 February has no match in a non-leap year; quarter-ends never hit this
            continue
        later = (cert, later_date)
        if later in index:
            pairs.append((grade, index[later]))
    matrix = migration_matrix(pairs)

    # Case study: frozen model, frozen scale, no refit.
    case_rows = []
    for o in case:
        p = calibrator.calibrate(model.predict_pd(std.transform(o.features)))
        case_rows.append(CaseRow(o.cert, o.report_date, p, scale.grade(p), o.label))

    return Week4Results(
        counts=split.counts(),
        dropped_incomplete=dropped,
        coefficients=coefficients,
        intercept=model.intercept,
        sign_problems=problems,
        sensitivity=sensitivity,
        calibrator=calibrator,
        cutoffs=scale.cutoffs,
        validation=_metrics("validation", val_pd, val_y),
        test=_metrics("test", test_pd, test_y),
        decile_validation=decile_table(val_pd, val_y),
        decile_test=test_deciles,
        riskiest_decile_share_test=share_of_failures_in_riskiest_decile(test_deciles),
        psi_by_input=psi_by_input,
        benchmark_auc_test={
            "model": auc(model_s, bench_y),
            "baseline": auc(base_s, bench_y),
            "expert": auc(expert_s, bench_y),
        },
        spearman_model_expert=spearman(model_s, expert_s),
        spearman_model_baseline=spearman(model_s, base_s),
        overlap_model_expert=riskiest_overlap(model_s, expert_s, RISKIEST_SHARE),
        overlap_model_baseline=riskiest_overlap(model_s, base_s, RISKIEST_SHARE),
        grade_rows_test=grade_rows,
        risk_ordered_test=is_risk_ordered(grade_rows),
        missed=missed,
        migration=matrix,
        migration_stay=migration_row_shares(matrix),
        case_study=case_rows,
    )


def format_week4(r: Week4Results) -> str:
    lines = ["Week 4 (Module B part 2): fit, calibrate, validate. Test set scored once.", ""]
    lines.append("Sets and event counts (before dropping incomplete rows):")
    for c in r.counts:
        lines.append(f"  {c.label:<34} {c.bank_quarters} bank-quarters, {c.events} events")
    lines.append("Rows dropped for a missing ratio: " + ", ".join(f"{k} {v}" for k, v in r.dropped_incomplete.items()))

    lines += ["", "Coefficients (standardised inputs; expected sign in brackets):"]
    expected = {"equity_to_assets": "-", "tier1_leverage": "-", "allowance_to_loans": "+",
                "roa_annualised": "-", "loans_to_deposits": "+", "efficiency_ratio": "+"}
    for n, c in r.coefficients.items():
        lines.append(f"  {n:<20} {c:+.4f}  [{expected[n]}]")
    lines.append(f"  intercept            {r.intercept:+.4f}")
    lines.append("Sign check: " + ("all coefficients match the expected direction" if not r.sign_problems
                                   else "MISMATCH in " + ", ".join(r.sign_problems)))

    lines += ["", "Drop-one-year sensitivity (largest coefficient move, sign flips):"]
    for s in r.sensitivity:
        flips = ", ".join(s.sign_flips) if s.sign_flips else "none"
        lines.append(f"  without {s.year}: max move {s.max_abs_change:.4f}, sign flips: {flips}")

    lines += ["", f"Platt calibration (fitted on validation): slope {r.calibrator.slope:.4f}, "
                  f"intercept {r.calibrator.intercept:.4f}"]
    lines += ["", "Master scale cut-offs (10 grades, from validation): "
                  + ", ".join(f"{c:.5f}" for c in r.cutoffs)]

    lines += ["", "Discrimination:"]
    for m in (r.validation, r.test):
        lines.append(f"  {m.name:<10} AUC {m.auc:.3f}, Gini {m.gini:.3f}, KS {m.ks:.3f}")
    lines.append(f"  riskiest decile holds {r.riskiest_decile_share_test:.1%} of test failures")

    lines += ["", "Calibration by decile, test (1 = riskiest):"]
    lines.append("  decile  count  failures  mean predicted  observed")
    for d in r.decile_test:
        lines.append(f"  {d.decile:>6}  {d.count:>5}  {d.failures:>8}  {d.mean_predicted:>14.4f}  {d.observed_rate:>8.4f}")

    lines += ["", "PSI, development vs test (below 0.10 stable, above 0.25 major shift):"]
    for n, v in r.psi_by_input.items():
        lines.append(f"  {n:<20} {v:.4f}")

    b = r.benchmark_auc_test
    lines += ["", "Benchmarks on the test set:",
              f"  AUC: model {b['model']:.3f}, baseline {b['baseline']:.3f}, expert {b['expert']:.3f}",
              f"  Spearman, model vs expert {r.spearman_model_expert:.3f}, model vs baseline {r.spearman_model_baseline:.3f}",
              f"  Riskiest 10% agreement, model vs expert {r.overlap_model_expert:.1%}, "
              f"model vs baseline {r.overlap_model_baseline:.1%}"]

    lines += ["", "Master scale, test: observed failure rate by grade:"]
    for g in r.grade_rows_test:
        lines.append(f"  grade {g.grade:>2}: {g.count:>5} bank-quarters, {g.failures:>3} failures, rate {g.failure_rate:.4f}")
    lines.append("Grades order risk correctly: " + ("yes" if r.risk_ordered_test else "NO"))

    lines += ["", f"Error review: failures placed in grades 1 to {MISSED_SAFEST_GRADES} on test: {len(r.missed)}"]
    for m in r.missed[:10]:
        lines.append(f"  cert {m.cert}, {m.report_date}, PD {m.probability:.4f}, grade {m.grade}")

    lines += ["", "One-year migration, test set (rows: grade now; columns: grade one year later):"]
    for i, row in enumerate(r.migration, start=1):
        share = r.migration_stay[i - 1]
        stay = "no bank" if share is None else f"{share:.1%} stay"
        lines.append(f"  grade {i:>2}: " + " ".join(f"{v:>5}" for v in row) + f"  ({stay})")

    lines += ["", f"Case study, frozen model ({len(r.case_study)} bank-quarters, 2022 Q4 to 2023 Q1):"]
    for c in sorted(r.case_study, key=lambda x: x.pd, reverse=True)[:10]:
        outcome = "failed in horizon" if c.label else "did not fail in horizon"
        lines.append(f"  cert {c.cert}, {c.report_date}, PD {c.pd:.4f}, grade {c.grade}, {outcome}")

    lines += ["", "Limitations:",
              "  Output is an illustrative model on public FDIC data. It is not an IFRS 9 or regulatory rating.",
              "  Test window ends 2022 Q3; the case study quarters are kept out of every other set.",
              "  Tier 1 leverage and efficiency ratio units are provisional until checked against raw FDIC fields.",
              "  The securities-loss and uninsured-deposit case study test was NOT done: the FDIC fields are not loaded.",
              "  Grades come from validation data only, so the test result is not tuned to the test set."]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    from pathlib import Path

    from credit_risk.config import ProjectPaths

    paths = ProjectPaths.default()
    reports: Path = paths.root / "reports"
    marker = reports / MARKER_NAME
    if marker.exists():
        print(f"The test set was already scored ({marker.read_text(encoding='utf-8').strip()}). "
              "It is used once, so this run stops here.")
        return 1

    import duckdb

    from credit_risk.scorecard.labels import build_observations
    from credit_risk.scorecard.panel import load_panel

    warehouse = paths.warehouse_file
    if not warehouse.exists():
        print(f"Warehouse not found at {warehouse}. Run make load first.")
        return 1
    con = duckdb.connect(str(warehouse), read_only=True)
    try:
        panel, failures = load_panel(con)
    finally:
        con.close()
    data_end = max(report_date for _, report_date, _ in panel)
    observations = build_observations(panel, failures, data_end=data_end)

    results = run_week4(observations)
    # Mark the test set as used before printing, so a formatting problem cannot cause a second look.
    reports.mkdir(parents=True, exist_ok=True)
    marker.write_text(datetime.now().isoformat(timespec="seconds") + "\n", encoding="utf-8")
    text = format_week4(results)
    (reports / RESULTS_NAME).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
