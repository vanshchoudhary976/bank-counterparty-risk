"""Module C step 5: concentration, wrong-way risk, expected loss and the collateral gap. All illustrative."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from credit_risk.exposure.collateral import collateralised_exposure
from credit_risk.exposure.limits import LIMIT_PCT_BY_GRADE, counterparty_pfe, limit_for_grade, status, utilisation
from credit_risk.exposure.portfolio import Counterparty, Trade
from credit_risk.exposure.simulate import N_PATHS, PFE_QUANTILE, SEED, net_value, simulate_factors

# Validation failure counts and bank-quarters by grade, from the Week 4 grade table (latest run).
GRADE_TABLE = {
    1: (0, 6265), 2: (0, 9421), 3: (0, 11310), 4: (0, 12021), 5: (1, 11711),
    6: (2, 10003), 7: (0, 7502), 8: (1, 5716), 9: (2, 4628), 10: (457, 6822),
}
PD_FLOOR = 0.0005  # assumption: no grade is treated as riskless
LGD_BASE = 0.45  # assumption: unsecured senior exposure
LGD_SENSITIVITY = (0.25, 0.45, 0.60)
WRONG_WAY_FACTOR = 1.5  # assumption: repo exposure rises by this factor after a downgrade
DOWNGRADE_GRADES = 2


def pd_for_grade(grade: int) -> float:
    if grade not in GRADE_TABLE:
        raise ValueError(f"grade must be 1 to 10, got {grade}")
    failures, count = GRADE_TABLE[grade]
    return max(failures / count, PD_FLOOR)


def concentration(peaks: dict[int, float]) -> dict[str, float]:
    """Top-5 share and Herfindahl-Hirschman index (0 to 10,000) of peak exposure by counterparty."""
    total = sum(v for v in peaks.values() if v > 0)
    if total <= 0:
        return {"top5_share": 0.0, "hhi": 0.0}
    shares = sorted((v / total for v in peaks.values() if v > 0), reverse=True)
    return {"top5_share": float(sum(shares[:5])), "hhi": float(sum(s * s for s in shares) * 10_000)}


def wrong_way_pfe(trades: list[Trade], paths: int = N_PATHS, seed: int = SEED) -> float:
    """Peak collateralised PFE after the wrong-way factor.

    Assumption: repo collateral is the counterparty's own securities, so it loses value as the
    counterparty weakens. The factor is therefore applied to post-margin exposure of any
    counterparty with a repo trade, rather than to the trade size.
    """
    horizon = max(t.maturity_years for t in trades)
    factors = simulate_factors(horizon, paths=paths, seed=seed)
    net = net_value(trades, factors)
    exposure = collateralised_exposure(net, has_agreement=any(t.collateralised for t in trades))
    if any(t.kind == "REPO" for t in trades):
        exposure = exposure * WRONG_WAY_FACTOR
    return float(np.quantile(exposure, PFE_QUANTILE, axis=0).max())


def uncollateralised_peak(trades: list[Trade], paths: int = N_PATHS, seed: int = SEED) -> float:
    horizon = max(t.maturity_years for t in trades)
    factors = simulate_factors(horizon, paths=paths, seed=seed)
    exposure = np.maximum(net_value(trades, factors), 0.0)
    return float(np.quantile(exposure, PFE_QUANTILE, axis=0).max())


def collateral_gap_rows(counterparties: list[Counterparty], trades: list[Trade]) -> list[tuple]:
    rows = []
    for cp in counterparties:
        mine = [t for t in trades if t.cert == cp.cert]
        raw = uncollateralised_peak(mine)
        post = float(counterparty_pfe(mine).max())
        rows.append((cp.cert, cp.name, raw, post, raw - post))
    return rows


def expected_loss_rows(counterparties: list[Counterparty], peaks: dict[int, float]) -> list[tuple]:
    """EL = EAD x PD x LGD. EAD is the collateralised peak PFE (a simplification of the EAD definition)."""
    rows = []
    for cp in counterparties:
        ead = peaks[cp.cert]
        pd = pd_for_grade(cp.grade)
        rows.append((cp.cert, cp.name, ead, pd, {lgd: ead * pd * lgd for lgd in LGD_SENSITIVITY}))
    return rows


def wrong_way_rows(counterparties: list[Counterparty], trades: list[Trade]) -> list[tuple]:
    rows = []
    for cp in counterparties:
        mine = [t for t in trades if t.cert == cp.cert]
        base_peak = float(counterparty_pfe(mine).max())
        new_grade = min(cp.grade + DOWNGRADE_GRADES, 10)
        stressed_peak = wrong_way_pfe(mine)
        limit_now = limit_for_grade(cp.grade)
        limit_after = limit_for_grade(new_grade)
        rows.append(
            (
                cp.cert, cp.name, cp.grade, new_grade, base_peak, stressed_peak,
                utilisation(base_peak, limit_now), utilisation(stressed_peak, limit_after),
                status(utilisation(stressed_peak, limit_after)),
            )
        )
    return rows


def format_measures(cps, trades) -> str:
    peaks = {cp.cert: float(counterparty_pfe([t for t in trades if t.cert == cp.cert]).max()) for cp in cps}
    conc = concentration(peaks)
    lines = [
        "ILLUSTRATIVE. Invented trades and assumptions. Not a production model.",
        "",
        "Concentration (peak collateralised PFE by counterparty)",
        f"  top-5 share of total: {conc['top5_share']:.0%}",
        f"  Herfindahl-Hirschman index: {conc['hhi']:,.0f} (10,000 means one counterparty)",
        "  Not done: by bank business model and by country (not in the loaded data).",
        "",
        "Collateral gap (peak PFE without and with collateral, post margin period)",
    ]
    for cert, name, raw, post, gap in collateral_gap_rows(cps, trades):
        lines.append(f"  {name[:36]:<36} without {raw:>14,.0f}  with {post:>14,.0f}  gap {gap:>14,.0f}")
    lines += [
        "",
        f"Wrong-way risk: post-margin exposure x{WRONG_WAY_FACTOR} where repo is present, downgrade {DOWNGRADE_GRADES} grades",
    ]
    for cert, name, g0, g1, b, s, u0, u1, st in wrong_way_rows(cps, trades):
        util_after = "reduce-only" if u1 == float("inf") else f"{u1:.0%}"
        lines.append(
            f"  {name[:36]:<36} grade {g0}->{g1}  peak {b:>12,.0f} -> {s:>12,.0f}  util {u0:.0%} -> {util_after}  {st}"
        )
    lines += [
        "",
        f"Expected loss = EAD x PD x LGD. PD floor {PD_FLOOR:.2%}. LGD base {LGD_BASE:.0%}",
    ]
    for cert, name, ead, pd, by_lgd in expected_loss_rows(cps, peaks):
        sens = ", ".join(f"LGD {k:.0%}: {v:,.0f}" for k, v in by_lgd.items())
        lines.append(f"  {name[:36]:<36} EAD {ead:>14,.0f}  PD {pd:.4%}  {sens}")
    total = {lgd: sum(r[4][lgd] for r in expected_loss_rows(cps, peaks)) for lgd in LGD_SENSITIVITY}
    lines.append("  Total: " + ", ".join(f"LGD {k:.0%}: {v:,.0f}" for k, v in total.items()))
    return "\n".join(lines) + "\n"


def run(data_dir: Path, reports_dir: Path) -> str:
    from credit_risk.exposure.portfolio import read_portfolio
    from credit_risk.exposure.run_exposure import read_counterparties

    cps = read_counterparties(data_dir / "portfolio_counterparties.csv")
    trades = read_portfolio(data_dir / "portfolio_assumptions.csv")
    text = format_measures(cps, trades)
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "measures_results.txt").write_text(text, encoding="utf-8")
    return text


def main() -> int:
    from credit_risk.config import ProjectPaths

    paths = ProjectPaths.default()
    if not (paths.root / "data" / "portfolio_assumptions.csv").exists():
        print("Run the exposure step first: python -m credit_risk.exposure.run_exposure")
        return 1
    print(run(paths.root / "data", paths.root / "reports"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
