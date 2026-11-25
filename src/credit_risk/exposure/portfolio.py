"""Illustrative counterparty portfolio for Module C.

Every trade here is INVENTED. Real trading exposures are not public, so the
portfolio exists only to exercise the exposure, collateral and limit code.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np

SEED = 42
MIN_COUNTERPARTIES = 12
MAX_COUNTERPARTIES = 15
MIN_TRADES = 2
MAX_TRADES = 4
TRADE_KINDS = ("IRS", "FX_FORWARD", "REPO", "DEPOSIT")
COLLATERALISED_KINDS = ("IRS", "REPO")
MIN_MATURITY_YEARS = 0.5
MAX_MATURITY_YEARS = 5.0
NOTIONAL_MEDIAN = 25_000_000.0  # invented, in GBP-equivalent units
LABEL = "ILLUSTRATIVE"


@dataclass(frozen=True)
class Counterparty:
    cert: int
    name: str
    grade: int  # master scale grade, 1 (safest) to 10


@dataclass(frozen=True)
class Trade:
    trade_id: str
    cert: int
    kind: str
    notional: float
    maturity_years: float
    netting_set: str
    collateralised: bool
    direction: int  # +1 if the counterparty owes us on a rise in value, -1 otherwise


def _validate_counterparties(counterparties: list[Counterparty]) -> None:
    if not MIN_COUNTERPARTIES <= len(counterparties) <= MAX_COUNTERPARTIES:
        raise ValueError(f"need {MIN_COUNTERPARTIES} to {MAX_COUNTERPARTIES} counterparties, got {len(counterparties)}")
    if len({c.cert for c in counterparties}) != len(counterparties):
        raise ValueError("counterparty certs must be unique")
    if any(not 1 <= c.grade <= 10 for c in counterparties):
        raise ValueError("grades must be between 1 and 10")


def generate_portfolio(counterparties: list[Counterparty], seed: int = SEED) -> list[Trade]:
    """Build 2 to 4 invented trades per counterparty, reproducibly from the seed."""
    _validate_counterparties(counterparties)
    rng = np.random.default_rng(seed)
    trades: list[Trade] = []
    for cp in counterparties:
        n = int(rng.integers(MIN_TRADES, MAX_TRADES + 1))
        for k in range(1, n + 1):
            kind = TRADE_KINDS[int(rng.integers(0, len(TRADE_KINDS)))]
            notional = float(np.round(NOTIONAL_MEDIAN * rng.lognormal(0.0, 0.6), -5))
            # maturities on quarter steps, so monthly simulation dates line up
            steps = int(rng.integers(int(MIN_MATURITY_YEARS * 4), int(MAX_MATURITY_YEARS * 4) + 1))
            direction = 1 if rng.random() < 0.5 else -1
            if kind in ("DEPOSIT", "REPO"):
                direction = 1  # we lend cash: the counterparty owes us the cash back
            trades.append(
                Trade(
                    trade_id=f"{cp.cert}-{k}",
                    cert=cp.cert,
                    kind=kind,
                    notional=notional,
                    maturity_years=steps / 4,
                    netting_set=str(cp.cert),
                    collateralised=kind in COLLATERALISED_KINDS,
                    direction=direction,
                )
            )
    return trades


FIELDS = ("label", "trade_id", "cert", "kind", "notional", "maturity_years", "netting_set", "collateralised", "direction")


def write_portfolio(trades: list[Trade], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        for t in trades:
            writer.writerow(
                {
                    "label": LABEL,
                    "trade_id": t.trade_id,
                    "cert": t.cert,
                    "kind": t.kind,
                    "notional": f"{t.notional:.0f}",
                    "maturity_years": f"{t.maturity_years:.2f}",
                    "netting_set": t.netting_set,
                    "collateralised": str(t.collateralised).lower(),
                    "direction": t.direction,
                }
            )


def read_portfolio(path: Path) -> list[Trade]:
    with path.open(newline="") as fh:
        rows = list(csv.DictReader(fh))
    if any(r["label"] != LABEL for r in rows):
        raise ValueError("every trade row must carry the ILLUSTRATIVE label")
    return [
        Trade(
            trade_id=r["trade_id"],
            cert=int(r["cert"]),
            kind=r["kind"],
            notional=float(r["notional"]),
            maturity_years=float(r["maturity_years"]),
            netting_set=r["netting_set"],
            collateralised=r["collateralised"] == "true",
            direction=int(r["direction"]),
        )
        for r in rows
    ]
