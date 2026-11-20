"""Logistic regression on weight-of-evidence inputs, giving a probability of failure.

Why logistic regression: each coefficient has a sign and a size that can be read and explained,
and the output is a probability, which the master scale needs. Inputs are WoE values, so each
ratio enters on a common scale.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class FittedModel:
    feature_names: tuple[str, ...]
    intercept: float
    coefficients: tuple[float, ...]

    def log_odds_of_failure(self, inputs: Sequence[float]) -> float:
        if len(inputs) != len(self.coefficients):
            raise ValueError(f"expected {len(self.coefficients)} inputs, got {len(inputs)}")
        return self.intercept + sum(c * x for c, x in zip(self.coefficients, inputs))

    def predict_pd(self, inputs: Sequence[float]) -> float:
        z = self.log_odds_of_failure(inputs)
        if z >= 0:
            return 1.0 / (1.0 + math.exp(-z))
        exp_z = math.exp(z)
        return exp_z / (1.0 + exp_z)


def fit_logistic(
    rows: Sequence[Sequence[float]],
    labels: Sequence[int],
    feature_names: Sequence[str],
    C: float = 1.0,
) -> FittedModel:
    """Fit by maximum likelihood with L2 regularisation (scikit-learn; C is the inverse strength).

    Imported here so that the rest of the package works without scikit-learn installed.
    """
    from sklearn.linear_model import LogisticRegression

    if len(rows) != len(labels):
        raise ValueError("rows and labels must be the same length")
    if len(set(labels)) < 2:
        raise ValueError("need both failures and survivors to fit")
    if any(len(r) != len(feature_names) for r in rows):
        raise ValueError("every row must have one value per feature name")

    model = LogisticRegression(C=C, max_iter=1000)
    model.fit([list(map(float, r)) for r in rows], list(labels))
    return FittedModel(
        feature_names=tuple(feature_names),
        intercept=float(model.intercept_[0]),
        coefficients=tuple(float(c) for c in model.coef_[0]),
    )
