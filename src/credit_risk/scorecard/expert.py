"""Expert-weighted CAMELS score: a transparent benchmark that needs no fitting to outcomes.

Each ratio is turned into a percentile against the development set, so 1.0 means riskier than
every development bank on that ratio and 0.0 means safer than every one. Area weights are fixed
before any results are seen (blueprint example: capital 30%, asset quality 25%, earnings 15%,
liquidity 20%, efficiency 10%). The 30% for capital is split equally between its two ratios.

A bank with a missing ratio gets no expert score. We do not guess a value for it.
"""

from __future__ import annotations

from bisect import bisect_left, bisect_right
from typing import Mapping, Optional, Sequence

# (ratio name, higher value means riskier, weight in the total score)
EXPERT_RATIOS: tuple[tuple[str, bool, float], ...] = (
    ("tier1_leverage", False, 0.15),
    ("equity_to_assets", False, 0.15),
    ("allowance_to_loans", False, 0.25),
    ("roa_annualised", False, 0.15),
    ("loans_to_deposits", True, 0.20),
    ("efficiency_ratio", True, 0.10),
)


def expert_weights_total() -> float:
    return sum(weight for _, _, weight in EXPERT_RATIOS)


def risk_percentile(value: float, sorted_reference: Sequence[float], higher_is_riskier: bool) -> float:
    """Share of development banks that are safer than this value (0 = safest, 1 = riskiest).

    sorted_reference must be sorted ascending. Binary search keeps each lookup fast on
    the full development set.
    """
    n = len(sorted_reference)
    if higher_is_riskier:
        return bisect_right(sorted_reference, value) / n
    return (n - bisect_left(sorted_reference, value)) / n


class ExpertScore:
    def __init__(self) -> None:
        if abs(expert_weights_total() - 1.0) > 1e-9:
            raise ValueError("expert weights must add up to 1")
        self._reference: dict[str, list[float]] = {}

    def fit(self, development: Sequence[Mapping[str, Optional[float]]]) -> "ExpertScore":
        """Store the development-set values that define the percentiles. Uses no labels."""
        for name, _, _ in EXPERT_RATIOS:
            values = [row[name] for row in development if row.get(name) is not None]
            if not values:
                raise ValueError(f"no development values for {name}")
            self._reference[name] = sorted(values)
        return self

    def score(self, features: Mapping[str, Optional[float]]) -> Optional[float]:
        if not self._reference:
            raise ValueError("call fit() before score()")
        total = 0.0
        for name, higher_is_riskier, weight in EXPERT_RATIOS:
            value = features.get(name)
            if value is None:
                return None
            total += weight * risk_percentile(value, self._reference[name], higher_is_riskier)
        return total
