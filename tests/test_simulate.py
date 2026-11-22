import numpy as np
import pytest

from credit_risk.exposure.portfolio import Trade
from credit_risk.exposure.simulate import (
    exposure_profiles,
    netting_set_exposure,
    simulate_factors,
    trade_value,
    zero_bond,
)


def _trade(kind="IRS", direction=1, notional=1e6, maturity=2.0, cert=1, tid="1-1"):
    return Trade(trade_id=tid, cert=cert, kind=kind, notional=notional, maturity_years=maturity,
                 netting_set=str(cert), collateralised=False, direction=direction)


def test_same_seed_repeats_exactly():
    a = simulate_factors(2.0, paths=200, seed=7)
    b = simulate_factors(2.0, paths=200, seed=7)
    assert np.array_equal(a.rate, b.rate) and np.array_equal(a.fx, b.fx)


def test_zero_bond_is_one_at_zero_maturity_and_falls_with_rate():
    assert zero_bond(np.array([0.03]), 0.0)[0] == pytest.approx(1.0)
    assert zero_bond(np.array([0.05]), 3.0)[0] < zero_bond(np.array([0.01]), 3.0)[0]


def test_trade_value_is_zero_after_maturity():
    f = simulate_factors(2.0, paths=50, seed=1)
    v = trade_value(_trade(maturity=1.0), 1.5, f.rate[:, 18], f.fx[:, 18])
    assert np.all(v == 0)


def test_deposit_exposure_is_principal_until_maturity():
    f = simulate_factors(2.0, paths=50, seed=1)
    v = trade_value(_trade(kind="DEPOSIT", notional=5.0), 0.5, f.rate[:, 6], f.fx[:, 6])
    assert np.all(v == 5.0)


def test_netting_reduces_exposure():
    f = simulate_factors(2.0, paths=500, seed=3)
    pos = _trade(kind="DEPOSIT", direction=1, tid="a")
    neg = _trade(kind="DEPOSIT", direction=-1, notional=1e6, tid="b")
    gross = netting_set_exposure([pos], f).sum() + netting_set_exposure([neg], f).sum()
    net = netting_set_exposure([pos, neg], f).sum()
    assert net <= gross


def test_exposure_is_never_negative_and_pfe_at_least_epe():
    trades = [_trade(kind="IRS", direction=-1, tid="x"), _trade(kind="FX_FORWARD", direction=1, tid="y")]
    (profile,) = exposure_profiles(trades, paths=500, seed=5)
    assert np.all(profile.epe >= 0)
    assert np.all(profile.pfe >= profile.epe - 1e-9)


def test_profiles_repeat_with_same_seed():
    trades = [_trade(tid="p"), _trade(kind="FX_FORWARD", tid="q")]
    a = exposure_profiles(trades, paths=300, seed=9)
    b = exposure_profiles(trades, paths=300, seed=9)
    assert np.array_equal(a[0].pfe, b[0].pfe)
