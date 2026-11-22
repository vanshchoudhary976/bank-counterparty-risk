"""Module D step 1 runner: stress each illustrative counterparty, re-score, and report grade, PD and limit changes."""

from __future__ import annotations

from pathlib import Path

from credit_risk.exposure.counterparties import SELECTION_QUARTER, fit_grader
from credit_risk.exposure.limits import counterparty_pfe, limit_for_grade, utilisation
from credit_risk.exposure.portfolio import read_portfolio
from credit_risk.exposure.run_exposure import read_counterparties
from credit_risk.stress.scenarios import SCENARIOS, Snapshot, features, stressed_features


def snapshots(con, certs: list[int]) -> dict[int, Snapshot]:
    rows = con.execute(
        "SELECT f.cert, f.total_assets, f.total_equity, f.net_loans, f.total_deposits, f.net_income, "
        "c.allowance_for_loans, c.tier1_leverage_pct, c.efficiency_ratio_pct "
        "FROM bank_financials f LEFT JOIN bank_capital_efficiency c "
        "ON c.cert = f.cert AND c.report_date = f.report_date "
        "WHERE f.report_date = ?",
        [SELECTION_QUARTER],
    ).fetchall()
    out = {}
    for cert, assets, equity, loans, deposits, ni, allow, t1, eff in rows:
        if cert not in certs:
            continue
        if None in (assets, equity, loans, deposits, ni, allow, t1):
            raise ValueError(f"cert {cert} is missing a stress input at {SELECTION_QUARTER}")
        out[int(cert)] = Snapshot(
            assets=float(assets), equity=float(equity), net_loans=float(loans), deposits=float(deposits),
            net_income=float(ni), allowance=float(allow), tier1=float(t1) / 100.0,
            efficiency=None if not eff else float(eff) / 100.0, month=SELECTION_QUARTER.month,
        )
    missing = set(certs) - set(out)
    if missing:
        raise ValueError(f"no balance sheet row for certs {sorted(missing)}")
    return out


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

    lines = [
        "ILLUSTRATIVE. Shocks are assumptions (see credit_risk/stress/scenarios.py). Balance sheets at "
        f"{SELECTION_QUARTER.isoformat()}.",
        "Grades and PDs come from the Week 4 scorecard. Limit utilisation uses the current collateralised peak PFE.",
        "",
    ]
    for cp in cps:
        s0 = snaps[cp.cert]
        peak = float(counterparty_pfe([t for t in trades if t.cert == cp.cert]).max())
        base_pd = pd_of(features(s0))
        base_grade = scale.grade(base_pd)
        lines.append(f"{cp.name} (cert {cp.cert}), base grade {base_grade}, base PD {base_pd:.4%}")
        for sc in SCENARIOS:
            f = stressed_features(s0, sc)
            pd_s = pd_of(f)
            grade_s = scale.grade(pd_s)
            util_s = utilisation(peak, limit_for_grade(grade_s))
            util_text = "reduce-only" if util_s == float("inf") else f"{util_s:.0%}"
            tier1_s = (s0.tier1 + (stressed_snap_equity_change(s0, sc)))
            lines.append(
                f"  {sc.name:<26} grade {grade_s:>2}  PD {pd_s:.4%}  tier1 {tier1_s:.2%}  limit util {util_text}"
            )
        lines.append("")
    text = "\n".join(lines) + "\n"
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "stress_results.txt").write_text(text, encoding="utf-8")
    return text


def stressed_snap_equity_change(s0: Snapshot, sc) -> float:
    from credit_risk.stress.scenarios import apply_scenario

    return apply_scenario(s0, sc).tier1 - s0.tier1


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
