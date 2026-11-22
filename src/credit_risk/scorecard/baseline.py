"""Single-ratio baseline: one threshold on one ratio. Shows what a simple screen achieves.

The threshold is set on the development set only, so that the flagged share of development banks
equals target_share. A bank is flagged when its ratio is below the threshold (low capital is risky).
Missing values are not flagged, and the count of missing values is reported rather than hidden.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional, Sequence


@dataclass(frozen=True)
class SingleRatioBaseline:
    ratio: str
    threshold: float

    def flags(self, features: Mapping[str, Optional[float]]) -> bool:
        value = features.get(self.ratio)
        return value is not None and value < self.threshold

    def risk_score(self, features: Mapping[str, Optional[float]]) -> Optional[float]:
        """Higher means riskier, so a lower ratio gives a higher score. Used for AUC."""
        value = features.get(self.ratio)
        return None if value is None else -value


def fit_single_ratio_baseline(
    development: Sequence[Mapping[str, Optional[float]]],
    ratio: str,
    target_share: float,
) -> SingleRatioBaseline:
    if not 0.0 < target_share < 1.0:
        raise ValueError("target_share must be between 0 and 1")
    values = sorted(row[ratio] for row in development if row.get(ratio) is not None)
    if not values:
        raise ValueError(f"no development values for {ratio}")
    position = max(0, min(len(values) - 1, round(target_share * len(values))))
    return SingleRatioBaseline(ratio=ratio, threshold=values[position])
