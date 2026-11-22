import pytest

from credit_risk.scorecard.standardise import Standardiser


def _rows():
    return [{"a": 1.0, "b": 10.0}, {"a": 3.0, "b": 20.0}, {"a": 5.0, "b": 30.0}]


def test_development_mean_and_spread_are_used():
    s = Standardiser(["a", "b"]).fit(_rows())
    assert s.parameters()["a"] == pytest.approx((3.0, 2.0))  # mean 3, sample sd 2
    assert s.transform({"a": 3.0, "b": 20.0}) == pytest.approx([0.0, 0.0])
    assert s.transform({"a": 5.0, "b": 10.0}) == pytest.approx([1.0, -1.0])


def test_missing_value_is_refused_not_guessed():
    s = Standardiser(["a", "b"]).fit(_rows())
    with pytest.raises(ValueError, match="missing"):
        s.transform({"a": 1.0, "b": None})


def test_constant_feature_is_refused():
    with pytest.raises(ValueError, match="no spread"):
        Standardiser(["a"]).fit([{"a": 2.0}, {"a": 2.0}])


def test_transform_before_fit_is_refused():
    with pytest.raises(ValueError, match="fit"):
        Standardiser(["a"]).transform({"a": 1.0})


def test_fit_uses_only_rows_given_to_it():
    s = Standardiser(["a"]).fit([{"a": 1.0}, {"a": 3.0}])
    assert s.parameters()["a"][0] == pytest.approx(2.0)
