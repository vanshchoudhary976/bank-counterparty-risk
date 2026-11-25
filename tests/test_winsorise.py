import pytest

from credit_risk.scorecard.winsorise import MIN_VALUES, Winsoriser


def _development():
    return [{"x": float(v)} for v in range(1, 101)]  # 1 to 100


def test_caps_are_the_interpolated_one_and_ninety_nine_percent_points():
    w = Winsoriser(["x"]).fit(_development())
    low, high = w.caps()["x"]
    assert low == pytest.approx(1.99)  # position 0.99 between 1 and 2
    assert high == pytest.approx(99.01)  # position 98.01 between 99 and 100


def test_values_inside_the_caps_are_unchanged():
    w = Winsoriser(["x"]).fit(_development())
    assert w.transform({"x": 50.0}) == {"x": 50.0}


def test_values_outside_the_caps_are_pulled_in():
    w = Winsoriser(["x"]).fit(_development())
    assert w.transform({"x": -1000.0})["x"] == pytest.approx(1.99)
    assert w.transform({"x": 1000.0})["x"] == pytest.approx(99.01)


def test_missing_values_stay_missing():
    w = Winsoriser(["x"]).fit(_development())
    assert w.transform({"x": None}) == {"x": None}


def test_missing_entries_in_development_are_ignored():
    dev = _development() + [{"x": None}] * 20
    w = Winsoriser(["x"]).fit(dev)
    assert w.caps()["x"][0] == pytest.approx(1.99)


def test_refuses_too_few_development_values():
    with pytest.raises(ValueError, match="need at least"):
        Winsoriser(["x"]).fit([{"x": float(v)} for v in range(MIN_VALUES - 1)])


def test_transform_refuses_before_fit():
    with pytest.raises(ValueError, match="fit"):
        Winsoriser(["x"]).transform({"x": 1.0})


def test_refuses_no_features():
    with pytest.raises(ValueError):
        Winsoriser([])
