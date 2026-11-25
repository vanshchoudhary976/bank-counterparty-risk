import numpy as np

from credit_risk.exposure.collateral import (
    MINIMUM_TRANSFER,
    THRESHOLD,
    collateral_held,
    collateralised_exposure,
    lagged_exposure,
)


def _net():
    rng = np.random.default_rng(0)
    return rng.normal(2_000_000, 3_000_000, size=(400, 30))


def test_collateral_never_raises_exposure():
    net = _net()
    with_csa = collateralised_exposure(net, has_agreement=True)
    lagged = lagged_exposure(net)
    assert np.all(with_csa <= lagged + 1e-9)


def test_no_agreement_means_no_collateral_effect():
    net = _net()
    assert np.array_equal(collateralised_exposure(net, has_agreement=False), lagged_exposure(net))


def test_collateral_zero_below_threshold_and_below_minimum_transfer():
    net = np.array([[THRESHOLD - 1, THRESHOLD + MINIMUM_TRANSFER / 2]])
    assert np.all(collateral_held(net) == 0)


def test_collateral_equals_excess_above_threshold():
    net = np.array([[THRESHOLD + 500_000.0]])
    assert collateral_held(net)[0, 0] == 500_000.0


def test_exposure_never_negative():
    assert np.all(collateralised_exposure(_net(), has_agreement=True) >= 0)
