import random

import pytest

from credit_risk.scorecard.calibration import PlattCalibrator, fit_platt, logit, sigmoid


def test_logit_and_sigmoid_are_inverses():
    assert sigmoid(logit(0.2)) == pytest.approx(0.2)


def test_platt_recovers_a_known_relationship():
    # The true failure rate is sigmoid(2 x logit(raw)), so raw probabilities are too close to 0.5.
    # A fixed seed makes the sample, and so the test, repeatable.
    rng = random.Random(7)
    raw = [rng.choice([0.01, 0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 0.9]) for _ in range(20000)]
    labels = [1 if rng.random() < sigmoid(2 * logit(p)) else 0 for p in raw]
    cal = fit_platt(raw, labels)
    assert cal.slope == pytest.approx(2.0, abs=0.15)
    assert cal.calibrate(0.5) == pytest.approx(0.5, abs=0.05)


def test_calibration_keeps_the_order_of_banks():
    cal = PlattCalibrator(slope=1.5, intercept=-0.3)
    raw = [0.01, 0.05, 0.2, 0.6]
    calibrated = [cal.calibrate(p) for p in raw]
    assert calibrated == sorted(calibrated)


def test_negative_slope_is_refused():
    raw = [0.1, 0.9] * 50
    labels = [1, 0] * 50  # riskier-looking banks survive more often: the scores point the wrong way
    with pytest.raises(ValueError, match="wrong way"):
        fit_platt(raw, labels)


def test_fit_refuses_one_class():
    with pytest.raises(ValueError):
        fit_platt([0.1, 0.2], [0, 0])
