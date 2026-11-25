"""Collateral and margin for Module C (step 3). Illustrative assumptions throughout."""

from __future__ import annotations

import numpy as np

THRESHOLD = 1_000_000.0  # invented, in the same units as notionals
MINIMUM_TRANSFER = 100_000.0  # invented
MARGIN_PERIOD_STEPS = 1  # 10 days, rounded up to one monthly step (conservative)


def collateral_held(net: np.ndarray, threshold: float = THRESHOLD, mta: float = MINIMUM_TRANSFER) -> np.ndarray:
    """Collateral the counterparty posts to us: the amount above the threshold, if it clears the minimum transfer."""
    excess = np.maximum(net - threshold, 0.0)
    return np.where(excess >= mta, excess, 0.0)


def lagged_exposure(net: np.ndarray, lag: int = MARGIN_PERIOD_STEPS) -> np.ndarray:
    """Exposure after the margin period of risk: the value lag steps later, floored at zero."""
    tail = np.repeat(net[:, -1:], lag, axis=1)
    return np.maximum(np.concatenate([net[:, lag:], tail], axis=1), 0.0)


def collateralised_exposure(net: np.ndarray, has_agreement: bool) -> np.ndarray:
    """Exposure after the margin period, less the collateral held at the start of the period."""
    after = lagged_exposure(net)
    if not has_agreement:
        return after
    return np.maximum(after - collateral_held(net), 0.0)
