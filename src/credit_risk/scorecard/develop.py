"""Development and validation refit on cleaned inputs. Never reads the test set or the case study.

Order:
1. Keep complete development and validation rows (every ratio present).
2. Winsorise each input at development 1st and 99th percentiles (rule 5), then standardise, on development only.
3. Fit the logistic model on development. Check signs. Run drop-one-year sensitivity.
4. Platt calibration and the 10-grade master scale, both from validation.
5. Validation discrimination and development-to-validation PSI.

Rows outside 2005 to 2013 are ignored by construction, so the test window cannot influence these results.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Sequence

from credit_risk.scorecard.calibration import PlattCalibrator, fit_platt
from credit_risk.scorecard.evaluation import GradeRow, auc, default_rate_by_grade, is_risk_ordered
from credit_risk.scorecard.labels import Observation
from credit_risk.scorecard.metrics import gini, ks_statistic, psi
from credit_risk.scorecard.model import fit_logistic
from credit_risk.scorecard.panel import RATIO_COLUMNS
from credit_risk.scorecard.scale import MasterScale, training_quantile_cutoffs
from credit_risk.scorecard.split import DEVELOPMENT, MIN_EVENTS, VALIDATION
from credit_risk.scorecard.standardise import Standardiser
from credit_risk.scorecard.validation import (
    MissedFailure,
    YearSensitivity,
    drop_one_year_sensitivity,
    missed_failures,
    sign_mismatches,
)
from credit_risk.scorecard.winsorise import Winsoriser

RESULTS_NAME = "development_results.txt"
MISSED_SAFEST_GRADES = 3


@dataclass(frozen=True)
class DevelopmentResults:
    dev_rows: int
    dev_events: int
    val_rows: int
    val_events: int
    dropped_incomplete: dict[str, int]
    caps: dict[str, tuple[float, float]]
    coefficients: dict[str, float]
    intercept: float
    sign_problems: list[str]
    sensitivity: list[YearSensitivity]
    calibrator: PlattCalibrator
    cutoffs: tuple[float, ...]
    val_auc: float
    val_gini: float
    val_ks: float
    psi_by_input: dict[str, float]
    grade_rows_val: list[GradeRow]
    risk_ordered_val: bool
    missed_val: list[MissedFailure]
    missed_val_count: int


def _complete(rows: Sequence[Observation]) -> list[Observation]:
    return [o for o in rows if all(o.features.get(n) is not None for n in RATIO_COLUMNS)]


def run_development(observations: Sequence[Observation]) -> DevelopmentResults:
    names = list(RATIO_COLUMNS)
    dev_all = [o for o in observations if DEVELOPMENT.contains(o.report_date)]
    val_all = [o for o in observations if VALIDATION.contains(o.report_date)]
    dev = _complete(dev_all)
    val = _complete(val_all)
    if not dev or not val:
        raise ValueError("development or validation is empty after dropping incomplete rows")
    dev_events = sum(o.label for o in dev)
    val_events = sum(o.label for o in val)
    if dev_events < MIN_EVENTS:
        raise ValueError(f"development has {dev_events} failures; the blueprint needs at least {MIN_EVENTS}")
    if len({o.label for o in val}) < 2:
        raise ValueError("validation needs both failures and survivors")

    winsoriser = Winsoriser(names).fit([o.features for o in dev])
    dev_w = [winsoriser.transform(o.features) for o in dev]
    val_w = [winsoriser.transform(o.features) for o in val]
    std = Standardiser(names).fit(dev_w)
    dev_z = [std.transform(f) for f in dev_w]
    val_z = [std.transform(f) for f in val_w]
    dev_y = [o.label for o in dev]
    val_y = [o.label for o in val]

    model = fit_logistic(dev_z, dev_y, names, C=1.0)
    coefficients = dict(zip(names, model.coefficients))

    def fit_coefficients(z_rows, labels):
        return dict(zip(names, fit_logistic(z_rows, labels, names, C=1.0).coefficients))

    sensitivity = drop_one_year_sensitivity(
        [(o.report_date.year, z, o.label) for o, z in zip(dev, dev_z)], names, fit_coefficients
    )

    val_raw = [model.predict_pd(z) for z in val_z]
    calibrator = fit_platt(val_raw, val_y)
    val_pd = [calibrator.calibrate(p) for p in val_raw]

    # Cut-offs come from development PDs only, so the validation grade table is out of sample.
    dev_pd = [calibrator.calibrate(model.predict_pd(z)) for z in dev_z]
    scale = MasterScale(training_quantile_cutoffs(dev_pd))
    val_grades = [scale.grade(p) for p in val_pd]
    grade_rows = default_rate_by_grade(val_grades, val_y)
    missed = missed_failures(
        [(o.cert, o.report_date, p, g, o.label) for o, p, g in zip(val, val_pd, val_grades)],
        safest_grade_limit=MISSED_SAFEST_GRADES,
    )

    return DevelopmentResults(
        dev_rows=len(dev),
        dev_events=dev_events,
        val_rows=len(val),
        val_events=val_events,
        dropped_incomplete={
            "development": len(dev_all) - len(dev),
            "validation": len(val_all) - len(val),
        },
        caps=winsoriser.caps(),
        coefficients=coefficients,
        intercept=model.intercept,
        sign_problems=sign_mismatches(coefficients),
        sensitivity=sensitivity,
        calibrator=calibrator,
        cutoffs=scale.cutoffs,
        val_auc=auc(val_pd, val_y),
        val_gini=gini(val_pd, val_y),
        val_ks=ks_statistic(val_pd, val_y),
        psi_by_input={n: psi([f[n] for f in dev_w], [f[n] for f in val_w]) for n in names},
        grade_rows_val=grade_rows,
        risk_ordered_val=is_risk_ordered(grade_rows),
        missed_val=missed,
        missed_val_count=len(missed),
    )


def format_development(r: DevelopmentResults) -> str:
    lines = ["Development and validation refit on cleaned inputs. Test set not read.", ""]
    lines.append(f"Development: {r.dev_rows} bank-quarters, {r.dev_events} failures")
    lines.append(f"Validation:  {r.val_rows} bank-quarters, {r.val_events} failures")
    lines.append("Dropped for a missing ratio: " + ", ".join(f"{k} {v}" for k, v in r.dropped_incomplete.items()))
    lines += ["", "Rule 5 caps (development 1st and 99th percentiles):"]
    for n, (lo, hi) in r.caps.items():
        lines.append(f"  {n:<20} {lo:>10.5f} {hi:>10.5f}")
    lines += ["", "Coefficients (standardised, winsorised inputs):"]
    for n, c in r.coefficients.items():
        lines.append(f"  {n:<20} {c:+.4f}")
    lines.append(f"  intercept            {r.intercept:+.4f}")
    lines.append("Sign check: " + ("all match the expected direction" if not r.sign_problems
                                   else "MISMATCH in " + ", ".join(r.sign_problems)))
    lines += ["", "Drop-one-year sensitivity (largest coefficient move, sign flips):"]
    for s in r.sensitivity:
        flips = ", ".join(s.sign_flips) if s.sign_flips else "none"
        lines.append(f"  without {s.year}: max move {s.max_abs_change:.4f}, sign flips: {flips}")
    lines += ["", f"Platt calibration (validation): slope {r.calibrator.slope:.4f}, intercept {r.calibrator.intercept:.4f}"]
    lines += ["", "Master scale cut-offs (validation): " + ", ".join(f"{c:.5f}" for c in r.cutoffs)]
    lines += ["", f"Validation discrimination: AUC {r.val_auc:.3f}, Gini {r.val_gini:.3f}, KS {r.val_ks:.3f}"]
    lines += ["", "PSI, development vs validation (below 0.10 stable, above 0.25 major shift):"]
    for n, v in r.psi_by_input.items():
        lines.append(f"  {n:<20} {v:.4f}")
    lines += ["", "Master scale, validation: observed failure rate by grade (1 = safest):"]
    for g in r.grade_rows_val:
        lines.append(f"  grade {g.grade:>2}: {g.count:>6} bank-quarters, {g.failures:>4} failures, rate {g.failure_rate:.5f}")
    lines.append("Grades order risk correctly: " + ("yes" if r.risk_ordered_val else "NO"))
    lines += ["", f"Missed failures: failures placed in grades 1 to {MISSED_SAFEST_GRADES} on validation: {r.missed_val_count}"]
    for m in r.missed_val[:10]:
        lines.append(f"  cert {m.cert}, {m.report_date}, PD {m.probability:.6f}, grade {m.grade}")
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
    text = format_development(run_development(observations))
    reports = paths.root / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    (reports / RESULTS_NAME).write_text(f"Run {datetime.now().isoformat(timespec='seconds')}\n{text}\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
