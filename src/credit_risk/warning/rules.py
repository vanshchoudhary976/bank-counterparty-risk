"""Module D step 2: transparent early-warning rules. Thresholds are fixed before the back-test and written down here.

Why these values: 6% Tier 1 leverage is an illustrative absolute floor, not a regulatory minimum. A loans-to-deposits
ratio above 100% means the bank lends more than it takes in deposits. Grade 8 and worse is the bottom three grades of
the master scale. A 25% and 40% asset growth bands follow the blueprint.
Not run: the non-current loans ratio and the securities unrealised-loss rule, because those fields are not loaded.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

TIER1_FLOOR = 0.06
LTD_RED = 1.00
GRADE_RED = 8
ASSET_GROWTH_AMBER = 0.25
ASSET_GROWTH_RED = 0.40
YEAR_QUARTERS = 4


@dataclass(frozen=True)
class Row:
    cert: int
    report_date: object  # date
    tier1: float
    ltd: float
    grade: int
    assets: float


@dataclass(frozen=True)
class PeerThresholds:
    tier1_p25: float
    ltd_p75: float


def peer_thresholds(rows: Sequence[Row]) -> PeerThresholds:
    import numpy as np

    return PeerThresholds(
        tier1_p25=float(np.percentile([r.tier1 for r in rows], 25)),
        ltd_p75=float(np.percentile([r.ltd for r in rows], 75)),
    )


def evaluate(hist: Sequence[Row], peers: PeerThresholds) -> list[tuple[str, str]]:
    """hist is one bank's rows sorted by date, ending with the quarter being assessed.
    Returns (rule, colour) for each rule that fires; colour is 'amber' or 'red'."""
    cur = hist[-1]
    fired: list[tuple[str, str]] = []

    if cur.tier1 < TIER1_FLOOR:
        fired.append(("tier1 below floor", "red"))
    elif cur.tier1 < peers.tier1_p25:
        fired.append(("tier1 below peer 25th percentile", "amber"))

    if len(hist) > YEAR_QUARTERS and cur.ltd > LTD_RED and _rising(hist, 4):
        fired.append(("loans to deposits above 100% and rising four quarters", "red"))
    elif cur.ltd > peers.ltd_p75:
        fired.append(("loans to deposits above peer 75th percentile", "amber"))

    if len(hist) >= 2:
        notches = cur.grade - hist[-2].grade
        if notches >= 2 or cur.grade >= GRADE_RED:
            fired.append(("rating downgrade of two notches or grade 8 and worse", "red"))
        elif notches >= 1:
            fired.append(("rating downgrade of one notch", "amber"))

    if len(hist) > YEAR_QUARTERS:
        growth = cur.assets / hist[-1 - YEAR_QUARTERS].assets - 1.0
        capital_falling = cur.tier1 < hist[-1 - YEAR_QUARTERS].tier1
        if growth > ASSET_GROWTH_RED and capital_falling:
            fired.append(("asset growth above 40% with falling capital", "red"))
        elif growth > ASSET_GROWTH_AMBER:
            fired.append(("asset growth above 25% a year", "amber"))
    return fired


def _rising(hist: Sequence[Row], quarters: int) -> bool:
    values = [r.ltd for r in hist[-(quarters + 1):]]
    return all(b > a for a, b in zip(values, values[1:]))


def colour(fired: Sequence[tuple[str, str]]) -> str:
    if any(c == "red" for _, c in fired):
        return "red"
    if fired:
        return "amber"
    return "green"
