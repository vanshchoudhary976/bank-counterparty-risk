"""Module D step 3 runner: expected loss and exposure under each stress scenario, per counterparty. Illustrative."""

from __future__ import annotations

from pathlib import Path

from credit_risk.exposure.counterparties import SELECTION_QUARTER, fit_grader
from credit_risk.exposure.limits import counterparty_pfe
from credit_risk.exposure.portfolio import read_portfolio
from credit_risk.exposure.run_exposure import read_counterparties
from credit_risk.stress.expected_loss import build_row, format_expected_loss
from credit_risk.stress.run_stress import snapshots
from credit_risk.stress.scenarios import SCENARIOS, features, stressed_features


def run(warehouse_file: Path, data_dir: Path, reports_dir: Path) -> str:
    import duckdb

    from credit_risk.scorecard.labels import build_observations
    from credit_risk.scorecard.panel import load_panel

    cps = read_counterparties(data_dir / "portfolio_counterparties.csv")
    trades = read_portfolio(data_dir / "portfolio_assumptions.csv")
    certs = [c.cert for c in cps]
    con = duckdb.connect(str(warehouse_file), read_only=True)
    try:
        snaps = snapshots(con, certs)
        panel, failures = load_panel(con, view="clean_scorecard_inputs")
    finally:
        con.close()
    observations = build_observations(panel, failures, data_end=max(d for _, d, _ in panel))
    pd_of, scale = fit_grader(observations)

    rows = []
    for cp in cps:
        s0 = snaps[cp.cert]
        mine = [t for t in trades if t.cert == cp.cert]
        base_ead = float(counterparty_pfe(mine).max())
        has_repo = any(t.kind == "REPO" for t in mine)
        base_grade = scale.grade(pd_of(features(s0)))
        for sc in SCENARIOS:
            if sc.name == "Base":
                continue
            stressed_grade = scale.grade(pd_of(stressed_features(s0, sc)))
            rows.append(
                build_row(cp.cert, cp.name, sc.name, base_grade, stressed_grade, base_ead, has_repo)
            )
    text = f"Balance sheets at {SELECTION_QUARTER.isoformat()}.\n" + format_expected_loss(rows)
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "expected_loss_stress.txt").write_text(text, encoding="utf-8")
    return text


def main() -> int:
    from credit_risk.config import ProjectPaths

    paths = ProjectPaths.default()
    if not paths.warehouse_file.exists():
        print(f"Warehouse not found at {paths.warehouse_file}. Run make load first.")
        return 1
    if not (paths.root / "data" / "portfolio_assumptions.csv").exists():
        print("Run the exposure step first: python -m credit_risk.exposure.run_exposure")
        return 1
    print(run(paths.warehouse_file, paths.root / "data", paths.root / "reports"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
