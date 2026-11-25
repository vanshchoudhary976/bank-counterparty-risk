"""Module C step 2 runner: portfolio file, exposure profiles, peak PFE table."""

from __future__ import annotations

import csv
from pathlib import Path

from credit_risk.exposure.portfolio import Counterparty, generate_portfolio, write_portfolio
from credit_risk.exposure.simulate import N_PATHS, SEED, exposure_profiles


def read_counterparties(path: Path) -> list[Counterparty]:
    with path.open(newline="") as fh:
        rows = list(csv.DictReader(fh))
    if any(r["label"] != "ILLUSTRATIVE" for r in rows):
        raise ValueError("counterparty rows must carry the ILLUSTRATIVE label")
    return [Counterparty(cert=int(r["cert"]), name=r["name"], grade=int(r["grade"])) for r in rows]


def run(data_dir: Path, reports_dir: Path) -> str:
    cps = read_counterparties(data_dir / "portfolio_counterparties.csv")
    trades = generate_portfolio(cps, seed=SEED)
    write_portfolio(trades, data_dir / "portfolio_assumptions.csv")
    profiles = exposure_profiles(trades, paths=N_PATHS, seed=SEED)
    by_cert = {c.cert: c for c in cps}
    lines = [
        "ILLUSTRATIVE portfolio. Trades are invented. Counterparties are real banks graded by the scorecard.",
        f"Simplified Monte Carlo, {N_PATHS} paths, seed {SEED}. Not a production model.",
        "",
        f"{'cert':>7}  {'name':<40} {'grade':>5}  {'peak PFE':>16}  {'max EPE':>16}",
    ]
    for p in sorted(profiles, key=lambda x: -x.peak_pfe):
        cp = by_cert[p.cert]
        lines.append(
            f"{p.cert:>7}  {cp.name[:40]:<40} {cp.grade:>5}  {p.peak_pfe:>16,.0f}  {float(p.epe.max()):>16,.0f}"
        )
    text = "\n".join(lines) + "\n"
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "exposure_results.txt").write_text(text, encoding="utf-8")
    return text


def main() -> int:
    from credit_risk.config import ProjectPaths

    paths = ProjectPaths.default()
    src = paths.root / "data" / "portfolio_counterparties.csv"
    if not src.exists():
        print("Run the counterparty selection first: python -m credit_risk.exposure.counterparties")
        return 1
    print(run(paths.root / "data", paths.root / "reports"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
