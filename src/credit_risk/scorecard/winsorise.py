"""Cap each input at the 1st and 99th percentiles of development data (cleaning rule 5).

Why: a few impossible or extreme values stretch the spread of an input, which shrinks every normal
bank's standardised value and destabilises the coefficients. Capping keeps the rank order and limits
the pull of those values. The caps come from development data only, so validation and test cannot
change them.
Percentiles use linear interpolation, the same method as DuckDB's quantile_cont.
"""

from __future__ import annotations

from typing import Mapping, Optional, Sequence

MIN_VALUES = 100  # too few values make a percentile cap meaningless


def _percentile(sorted_values: Sequence[float], q: float) -> float:
    position = q * (len(sorted_values) - 1)
    low = int(position)
    high = min(low + 1, len(sorted_values) - 1)
    return sorted_values[low] + (position - low) * (sorted_values[high] - sorted_values[low])


class Winsoriser:
    LOWER_Q = 0.01
    UPPER_Q = 0.99

    def __init__(self, feature_names: Sequence[str]) -> None:
        if not feature_names:
            raise ValueError("need at least one feature")
        self.feature_names = tuple(feature_names)
        self._caps: dict[str, tuple[float, float]] = {}

    def fit(self, development: Sequence[Mapping[str, Optional[float]]]) -> "Winsoriser":
        for name in self.feature_names:
            values = sorted(row[name] for row in development if row.get(name) is not None)
            if len(values) < MIN_VALUES:
                raise ValueError(f"need at least {MIN_VALUES} development values for {name}, got {len(values)}")
            self._caps[name] = (_percentile(values, self.LOWER_Q), _percentile(values, self.UPPER_Q))
        return self

    def transform(self, features: Mapping[str, Optional[float]]) -> dict[str, Optional[float]]:
        if not self._caps:
            raise ValueError("fit must be called before transform")
        out: dict[str, Optional[float]] = {}
        for name in self.feature_names:
            value = features.get(name)
            if value is None:
                out[name] = None
                continue
            low, high = self._caps[name]
            out[name] = min(max(value, low), high)
        return out

    def caps(self) -> dict[str, tuple[float, float]]:
        return dict(self._caps)
