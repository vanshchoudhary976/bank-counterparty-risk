"""Choose the 12 illustrative counterparties and grade them with the Week 4 scorecard.

Selection: banks that report in the chosen quarter with total assets above a floor,
drawn reproducibly with the portfolio seed. Grading: the same steps as run_development
(winsorise, standardise, logistic fit on development, Platt calibration on validation,
master scale from development PDs), then the scorecard PD of each selected bank.
"""

from __future__ import annotations

from datetime import date
from typing import Mapping, Sequence

import numpy as np

from credit_risk.exposure.portfolio import Counterparty, MAX_COUNTERPARTIES, MIN_COUNTERPARTIES, SEED
from credit_risk.scorecard.calibration import fit_platt
from credit_risk.scorecard.labels import Observation
from credit_risk.scorecard.model import fit_logistic
from credit_risk.scorecard.panel import RATIO_COLUMNS
from credit_risk.scorecard.scale import MasterScale, training_quantile_cutoffs
from credit_risk.scorecard.split import DEVELOPMENT, VALIDATION
from credit_risk.scorecard.standardise import Standardiser
from credit_risk.scorecard.winsorise import Winsoriser

SELECTION_QUARTER = date(2022, 12, 31)
MIN_TOTAL_ASSETS = 1_000_000.0  # thousands of dollars, as the FDIC reports it (1,000,000 = $1bn)
COUNTERPARTY_COUNT = 12


def eligible_certs(assets_by_cert: Mapping[int, float], min_assets: float = MIN_TOTAL_ASSETS) -> list[int]:
    """Certs whose total assets in the selection quarter clear the floor, sorted for reproducibility."""
    return sorted(cert for cert, assets in assets_by_cert.items() if assets is not None and assets >= min_assets)


def select_certs(certs: Sequence[int], count: int = COUNTERPARTY_COUNT, seed: int = SEED) -> list[int]:
    if not MIN_COUNTERPARTIES <= count <= MAX_COUNTERPARTIES:
        raise ValueError(f"count must be {MIN_COUNTERPARTIES} to {MAX_COUNTERPARTIES}")
    if len(certs) < count:
        raise ValueError(f"need at least {count} eligible banks, got {len(certs)}")
    rng = np.random.default_rng(seed)
    picked = rng.choice(np.array(sorted(certs)), size=count, replace=False)
    return sorted(int(c) for c in picked)


def _complete(rows: Sequence[Observation]) -> list[Observation]:
    return [o for o in rows if all(o.features.get(n) is not None for n in RATIO_COLUMNS)]


def fit_grader(observations: Sequence[Observation]):
    """Fit the Week 4 scorecard on development and calibrate on validation. Returns a scoring function and the master scale."""
    dev = _complete([o for o in observations if DEVELOPMENT.contains(o.report_date)])
    val = _complete([o for o in observations if VALIDATION.contains(o.report_date)])
    if not dev or not val:
        raise ValueError("development or validation is empty after dropping incomplete rows")
    names = list(RATIO_COLUMNS)
    winsoriser = Winsoriser(names).fit([o.features for o in dev])
    std = Standardiser(names).fit([winsoriser.transform(o.features) for o in dev])

    def z_of(features: Mapping[str, float | None]) -> list[float]:
        return std.transform(winsoriser.transform(features))

    model = fit_logistic([z_of(o.features) for o in dev], [o.label for o in dev], names, C=1.0)
    calibrator = fit_platt([model.predict_pd(z_of(o.features)) for o in val], [o.label for o in val])
    dev_pd = [calibrator.calibrate(model.predict_pd(z_of(o.features))) for o in dev]
    scale = MasterScale(training_quantile_cutoffs(dev_pd))

    def pd_of(features: Mapping[str, float | None]) -> float:
        return calibrator.calibrate(model.predict_pd(z_of(features)))

    return pd_of, scale


def grade_counterparties(
    observations: Sequence[Observation], selected: Sequence[Mapping[str, object]]
) -> list[Counterparty]:
    """selected rows carry cert, name and features for the selection quarter."""
    pd_of, scale = fit_grader(observations)
    out = []
    for row in selected:
        grade = scale.grade(pd_of(row["features"]))  # type: ignore[arg-type]
        out.append(Counterparty(cert=int(row["cert"]), name=str(row["name"]), grade=grade))
    return out


def run_selection(warehouse_file, output_dir) -> list[Counterparty]:
    """Read the warehouse, pick 12 active banks with assets above the floor, grade them, and write the CSV."""
    import csv
    from pathlib import Path

    import duckdb

    from credit_risk.scorecard.labels import build_observations
    from credit_risk.scorecard.panel import load_panel

    con = duckdb.connect(str(warehouse_file), read_only=True)
    try:
        panel, failures = load_panel(con, view="clean_scorecard_inputs")
        assets_rows = con.execute(
            "SELECT f.cert, f.total_assets FROM bank_financials f "
            "JOIN institutions i ON i.cert = f.cert "
            "WHERE f.report_date = ? AND i.active",
            [SELECTION_QUARTER],
        ).fetchall()
        names = dict(con.execute("SELECT cert, bank_name FROM institutions").fetchall())
    finally:
        con.close()

    assets = {int(c): a for c, a in assets_rows}
    chosen = select_certs(eligible_certs(assets))
    panel_by_key = {(c, d): f for c, d, f in panel}
    selected_rows = []
    for cert in chosen:
        feats = panel_by_key.get((cert, SELECTION_QUARTER))
        if feats is None:
            raise ValueError(f"cert {cert} has no complete scorecard row for {SELECTION_QUARTER}")
        selected_rows.append({"cert": cert, "name": names.get(cert) or f"Bank {cert}", "features": feats})

    data_end = max(d for _, d, _ in panel)
    observations = build_observations(panel, failures, data_end=data_end)
    counterparties = grade_counterparties(observations, selected_rows)

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    with (out / "portfolio_counterparties.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["label", "cert", "name", "grade", "selection_quarter"])
        for cp in counterparties:
            w.writerow(["ILLUSTRATIVE", cp.cert, cp.name, cp.grade, SELECTION_QUARTER.isoformat()])
    return counterparties


def main() -> int:
    from credit_risk.config import ProjectPaths

    paths = ProjectPaths.default()
    if not paths.warehouse_file.exists():
        print(f"Warehouse not found at {paths.warehouse_file}. Run make load first.")
        return 1
    cps = run_selection(paths.warehouse_file, paths.root / "data")
    print("Illustrative counterparties (selected from active banks with assets over $1bn at 2022 Q4):")
    for cp in cps:
        print(f"  cert {cp.cert}  {cp.name}  grade {cp.grade}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
