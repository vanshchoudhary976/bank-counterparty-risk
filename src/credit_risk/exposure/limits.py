"""Counterparty limits, utilisation and status bands for Module C (step 4). Everything here is illustrative."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from credit_risk.exposure.collateral import collateralised_exposure, lagged_exposure
from credit_risk.exposure.portfolio import Counterparty, Trade, read_portfolio
from credit_risk.exposure.simulate import (
    N_PATHS,
    PFE_QUANTILE,
    SEED,
    net_value,
    simulate_factors,
    trade_value,
)

CAPITAL_BASE = 5_000_000_000.0  # invented, assumed capital base in the same units as notionals
LIMIT_PCT_BY_GRADE = {1: 0.05, 2: 0.05, 3: 0.05, 4: 0.025, 5: 0.025, 6: 0.025, 7: 0.025, 8: 0.01, 9: 0.01, 10: 0.0}
GREEN_BELOW = 0.80
RED_ABOVE = 1.00


def limit_for_grade(grade: int, capital_base: float = CAPITAL_BASE) -> float:
    if grade not in LIMIT_PCT_BY_GRADE:
        raise ValueError(f"grade must be 1 to 10, got {grade}")
    return capital_base * LIMIT_PCT_BY_GRADE[grade]


def utilisation(peak_pfe: float, limit: float) -> float:
    if limit <= 0:
        return float("inf") if peak_pfe > 0 else 0.0
    return peak_pfe / limit


def status(util: float) -> str:
    if util > RED_ABOVE:
        return "red"
    if util >= GREEN_BELOW:
        return "amber"
    return "green"


@dataclass(frozen=True)
class LimitRow:
    cert: int
    name: str
    grade: int
    limit: float
    peak_pfe: float
    utilisation: float
    status: str
    reason: str
    drivers: tuple[str, ...]
    action: str


def counterparty_pfe(trades: list[Trade], paths: int = N_PATHS, seed: int = SEED) -> np.ndarray:
    """Collateralised PFE per date for one counterparty."""
    horizon = max(t.maturity_years for t in trades)
    factors = simulate_factors(horizon, paths=paths, seed=seed)
    net = net_value(trades, factors)
    exposure = collateralised_exposure(net, has_agreement=any(t.collateralised for t in trades))
    return np.quantile(exposure, PFE_QUANTILE, axis=0)


def _drivers(trades: list[Trade], paths: int, seed: int) -> tuple[str, ...]:
    horizon = max(t.maturity_years for t in trades)
    factors = simulate_factors(horizon, paths=paths, seed=seed)
    scored = []
    for t in trades:
        v = np.zeros_like(factors.rate)
        for i, d in enumerate(factors.dates):
            v[:, i] = trade_value(t, float(d), factors.rate[:, i], factors.fx[:, i])
        scored.append((float(np.maximum(v, 0).max()), t.trade_id, t.kind))
    scored.sort(reverse=True)
    return tuple(f"{tid} ({kind})" for _, tid, kind in scored[:2])


def build_limit_rows(
    counterparties: list[Counterparty], trades: list[Trade], paths: int = N_PATHS, seed: int = SEED
) -> list[LimitRow]:
    rows = []
    for cp in counterparties:
        mine = [t for t in trades if t.cert == cp.cert]
        if not mine:
            raise ValueError(f"no trades for cert {cp.cert}")
        peak = float(counterparty_pfe(mine, paths=paths, seed=seed).max())
        limit = limit_for_grade(cp.grade)
        util = utilisation(peak, limit)
        st = status(util)
        if limit <= 0 and peak > 0:
            reason = f"grade {cp.grade} is reduce-only and has positive exposure"
            action = "reduce-only: close out or reduce the exposure to zero, no new trades"
        elif st == "red":
            reason = f"peak PFE is {util:.0%} of the limit"
            action = f"reduce peak exposure by {peak - limit:,.0f} or obtain approval for an exception"
        elif st == "amber":
            reason = f"peak PFE is {util:.0%} of the limit, within the 80% to 100% band"
            action = "monitor; no new trades that raise peak PFE"
        else:
            reason = f"peak PFE is {util:.0%} of the limit"
            action = "none"
        rows.append(
            LimitRow(
                cert=cp.cert,
                name=cp.name,
                grade=cp.grade,
                limit=limit,
                peak_pfe=peak,
                utilisation=util,
                status=st,
                reason=reason,
                drivers=_drivers(mine, paths, seed) if st == "red" else (),
                action=action,
            )
        )
    return rows


def format_limits(rows: list[LimitRow]) -> str:
    lines = [
        "ILLUSTRATIVE. Limits are set from an invented capital base and grade percentages.",
        "Utilisation uses collateralised, post-margin peak PFE. Bands: green below 80%, amber 80% to 100%, red above 100%.",
        "",
        f"{'cert':>7}  {'name':<36} {'grade':>5}  {'limit':>14}  {'peak PFE':>14}  {'util':>7}  status",
    ]
    for r in sorted(rows, key=lambda x: -x.utilisation):
        util = "n/a" if r.utilisation == float("inf") else f"{r.utilisation:.0%}"
        lines.append(
            f"{r.cert:>7}  {r.name[:36]:<36} {r.grade:>5}  {r.limit:>14,.0f}  {r.peak_pfe:>14,.0f}  {util:>7}  {r.status}"
        )
    breaches = [r for r in rows if r.status == "red"]
    lines += ["", f"Breach report: {len(breaches)} counterparties above 100%"]
    for r in breaches:
        lines.append(f"  {r.name} (cert {r.cert}): {r.reason}")
        lines.append(f"    drivers: {', '.join(r.drivers) if r.drivers else 'none'}")
        lines.append(f"    action: {r.action}")
    return "\n".join(lines) + "\n"


def run(data_dir: Path, reports_dir: Path) -> str:
    from credit_risk.exposure.run_exposure import read_counterparties

    cps = read_counterparties(data_dir / "portfolio_counterparties.csv")
    trades = read_portfolio(data_dir / "portfolio_assumptions.csv")
    text = format_limits(build_limit_rows(cps, trades))
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "limits_results.txt").write_text(text, encoding="utf-8")
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
