"""Standardise each ratio to mean 0 and standard deviation 1, using development data only.

Why: a logistic coefficient is only comparable across ratios when they share one scale.
Why development only: the mean and spread must not be learned from validation or test data.
"""

from __future__ import annotations

import math
from typing import Mapping, Optional, Sequence


class Standardiser:
    def __init__(self, feature_names: Sequence[str]) -> None:
        if not feature_names:
            raise ValueError("need at least one feature")
        self.feature_names = tuple(feature_names)
        self._mean: dict[str, float] = {}
        self._sd: dict[str, float] = {}

    def fit(self, development: Sequence[Mapping[str, Optional[float]]]) -> "Standardiser":
        for name in self.feature_names:
            values = [row[name] for row in development if row.get(name) is not None]
            if len(values) < 2:
                raise ValueError(f"need at least two development values for {name}")
            mean = sum(values) / len(values)
            variance = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
            sd = math.sqrt(variance)
            if not math.isfinite(sd) or sd == 0.0:
                raise ValueError(f"{name} has no spread in the development data")
            self._mean[name] = mean
            self._sd[name] = sd
        return self

    def transform(self, features: Mapping[str, Optional[float]]) -> list[float]:
        if not self._mean:
            raise ValueError("call fit() before transform()")
        out = []
        for name in self.feature_names:
            value = features.get(name)
            if value is None:
                raise ValueError(f"{name} is missing; only complete rows can be scored")
            out.append((value - self._mean[name]) / self._sd[name])
        return out

    def parameters(self) -> dict[str, tuple[float, float]]:
        """Mean and standard deviation per feature, for the model documentation."""
        return {name: (self._mean[name], self._sd[name]) for name in self.feature_names}
