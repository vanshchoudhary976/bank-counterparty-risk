import math

import pytest

from credit_risk.scorecard.model import FittedModel, fit_logistic


def test_predict_pd_is_one_half_at_zero_log_odds():
    model = FittedModel(feature_names=("a",), intercept=0.0, coefficients=(0.0,))
    assert model.predict_pd([3.0]) == pytest.approx(0.5)


def test_predict_pd_uses_logistic_function():
    model = FittedModel(feature_names=("a", "b"), intercept=-1.0, coefficients=(2.0, 0.5))
    z = -1.0 + 2.0 * 1.0 + 0.5 * 2.0
    assert model.predict_pd([1.0, 2.0]) == pytest.approx(1 / (1 + math.exp(-z)))


def test_predict_pd_is_stable_for_large_negative_log_odds():
    model = FittedModel(feature_names=("a",), intercept=-1000.0, coefficients=(0.0,))
    assert model.predict_pd([0.0]) == pytest.approx(0.0, abs=1e-300)


def test_predict_rejects_wrong_number_of_inputs():
    model = FittedModel(feature_names=("a",), intercept=0.0, coefficients=(1.0,))
    with pytest.raises(ValueError, match="expected 1"):
        model.predict_pd([1.0, 2.0])


def test_fit_logistic_gives_negative_coefficient_when_low_woe_means_failure():
    # Low input values are failures, high values are survivors.
    xs = [[-3.0], [-2.5], [-2.0], [-1.0], [-0.5], [0.5], [1.0], [2.0], [2.5], [3.0]]
    ys = [1, 1, 1, 1, 0, 1, 0, 0, 0, 0]
    model = fit_logistic(xs, ys, feature_names=["woe_x"], C=1.0)
    assert model.feature_names == ("woe_x",)
    assert model.coefficients[0] < 0
    assert model.predict_pd([-3.0]) > model.predict_pd([3.0])


def test_fit_logistic_rejects_single_class_and_bad_shapes():
    with pytest.raises(ValueError, match="both failures and survivors"):
        fit_logistic([[1.0], [2.0]], [0, 0], feature_names=["x"])
    with pytest.raises(ValueError, match="same length"):
        fit_logistic([[1.0]], [0, 1], feature_names=["x"])
    with pytest.raises(ValueError, match="one value per feature"):
        fit_logistic([[1.0, 2.0], [1.0, 2.0]], [0, 1], feature_names=["x"])
