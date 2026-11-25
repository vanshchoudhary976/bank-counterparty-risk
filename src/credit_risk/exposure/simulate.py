"""Simplified Monte Carlo for current and potential future exposure (Module C, step 2).

This is NOT a production model. Interest rates follow a Vasicek (mean-reverting) model, FX follows
geometric Brownian motion, and trades are revalued in closed form. Repo and deposit exposure is
treated as the principal at risk for the rest of the term. Everything is illustrative.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from credit_risk.exposure.portfolio import Trade

N_PATHS = 5000
SEED = 42
STEPS_PER_YEAR = 12  # monthly dates
A_MEAN_REVERSION = 0.10  # invented
THETA_LONG_RATE = 0.03  # invented
SIGMA_RATE = 0.010  # invented
R0 = 0.03
FX_SIGMA = 0.10  # invented
FX0 = 1.0
SWAP_FIXED_RATE = 0.03  # invented
FX_STRIKE = 1.0
PFE_QUANTILE = 0.95


@dataclass(frozen=True)
class Factors:
    dates: np.ndarray  # year fractions, shape (T+1,)
    rate: np.ndarray  # shape (paths, T+1)
    fx: np.ndarray  # shape (paths, T+1)


def simulate_factors(horizon_years: float, paths: int = N_PATHS, seed: int = SEED) -> Factors:
    rng = np.random.default_rng(seed)
    steps = int(round(horizon_years * STEPS_PER_YEAR))
    dt = 1.0 / STEPS_PER_YEAR
    rate = np.empty((paths, steps + 1))
    fx = np.empty((paths, steps + 1))
    rate[:, 0] = R0
    fx[:, 0] = FX0
    decay = np.exp(-A_MEAN_REVERSION * dt)
    spread = SIGMA_RATE * np.sqrt((1 - decay**2) / (2 * A_MEAN_REVERSION))
    for k in range(steps):
        z1 = rng.standard_normal(paths)
        rate[:, k + 1] = THETA_LONG_RATE + (rate[:, k] - THETA_LONG_RATE) * decay + spread * z1
        z2 = rng.standard_normal(paths)
        fx[:, k + 1] = fx[:, k] * np.exp(-0.5 * FX_SIGMA**2 * dt + FX_SIGMA * np.sqrt(dt) * z2)
    return Factors(dates=np.arange(steps + 1) * dt, rate=rate, fx=fx)


def zero_bond(rate: np.ndarray, maturity: np.ndarray | float) -> np.ndarray:
    """Vasicek zero-coupon bond price, closed form."""
    m = np.asarray(maturity, dtype=float)
    b = (1 - np.exp(-A_MEAN_REVERSION * m)) / A_MEAN_REVERSION
    a = (THETA_LONG_RATE - SIGMA_RATE**2 / (2 * A_MEAN_REVERSION**2)) * (b - m) - SIGMA_RATE**2 * b**2 / (
        4 * A_MEAN_REVERSION
    )
    return np.exp(a - b * rate)


def trade_value(trade: Trade, t: float, rate: np.ndarray, fx: np.ndarray) -> np.ndarray:
    """Value to us of one trade at time t, per path. Positive means the counterparty owes us."""
    remaining = trade.maturity_years - t
    if remaining <= 0:
        return np.zeros_like(rate)
    if trade.kind == "IRS":
        # receive fixed, pay floating: annuity of quarterly payments less the floating leg
        quarters = int(np.ceil(remaining * 4))
        annuity = sum(0.25 * zero_bond(rate, min(k * 0.25, remaining)) for k in range(1, quarters + 1))
        value = trade.notional * (SWAP_FIXED_RATE * annuity - (1 - zero_bond(rate, remaining)))
    elif trade.kind == "FX_FORWARD":
        value = trade.notional * (fx - FX_STRIKE) * zero_bond(rate, remaining)
    elif trade.kind in ("DEPOSIT", "REPO"):
        value = np.full_like(rate, trade.notional)
    else:
        raise ValueError(f"unknown trade kind {trade.kind!r}")
    return trade.direction * value


def net_value(trades: list[Trade], factors: Factors) -> np.ndarray:
    """Signed sum of trade values per path and date for one netting set (before taking the positive part)."""
    total = np.zeros_like(factors.rate)
    for i, t_date in enumerate(factors.dates):
        net = np.zeros(factors.rate.shape[0])
        for trade in trades:
            net += trade_value(trade, float(t_date), factors.rate[:, i], factors.fx[:, i])
        total[:, i] = net
    return total


def netting_set_exposure(trades: list[Trade], factors: Factors) -> np.ndarray:
    """Exposure per path and date for one netting set: max(sum of trade values, 0)."""
    return np.maximum(net_value(trades, factors), 0.0)


@dataclass(frozen=True)
class ExposureProfile:
    cert: int
    dates: np.ndarray
    epe: np.ndarray  # expected positive exposure per date
    pfe: np.ndarray  # 95th percentile of exposure per date

    @property
    def peak_pfe(self) -> float:
        return float(self.pfe.max())


def exposure_profiles(trades: list[Trade], paths: int = N_PATHS, seed: int = SEED) -> list[ExposureProfile]:
    by_cert: dict[int, list[Trade]] = {}
    for t in trades:
        by_cert.setdefault(t.cert, []).append(t)
    horizon = max(t.maturity_years for t in trades)
    factors = simulate_factors(horizon, paths=paths, seed=seed)
    profiles = []
    for cert in sorted(by_cert):
        exp = netting_set_exposure(by_cert[cert], factors)
        profiles.append(
            ExposureProfile(
                cert=cert,
                dates=factors.dates,
                epe=exp.mean(axis=0),
                pfe=np.quantile(exp, PFE_QUANTILE, axis=0),
            )
        )
    return profiles
