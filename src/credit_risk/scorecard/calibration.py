"""Platt scaling: map raw failure probabilities onto observed failure rates.

Platt fits a logistic curve on log-odds of the raw probability, so calibrated = sigmoid(a + b x logit(raw)).
It is fitted on the validation set only, never on development or test data.
A positive slope b keeps the ranking of banks unchanged, so calibration does not change AUC.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

PD_FLOOR = 1e-9


def logit(p: float) -> float:
    p = min(max(p, PD_FLOOR), 1.0 - PD_FLOOR)
    return math.log(p / (1.0 - p))


def sigmoid(z: float) -> float:
    if z >= 0:
        return 1.0 / (1.0 + math.exp(-z))
    exp_z = math.exp(z)
    return exp_z / (1.0 + exp_z)


@dataclass(frozen=True)
class PlattCalibrator:
    slope: float
    intercept: float

    def calibrate(self, raw_pd: float) -> float:
        return sigmoid(self.intercept + self.slope * logit(raw_pd))


def fit_platt(raw_pds: Sequence[float], labels: Sequence[int]) -> PlattCalibrator:
    from sklearn.linear_model import LogisticRegression

    if len(raw_pds) != len(labels):
        raise ValueError("raw_pds and labels must be the same length")
    if len(set(labels)) < 2:
        raise ValueError("Platt scaling needs both failures and survivors")
    x = [[logit(p)] for p in raw_pds]
    # A very large C means almost no penalty, so this is a plain maximum-likelihood fit of two numbers.
    model = LogisticRegression(C=1e6, max_iter=1000)
    model.fit(x, list(labels))
    slope = float(model.coef_[0][0])
    if slope <= 0:
        raise ValueError(f"Platt slope is {slope:.4f}; a non-positive slope means the scores point the wrong way")
    return PlattCalibrator(slope=slope, intercept=float(model.intercept_[0]))
