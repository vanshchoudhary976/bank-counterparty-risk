import math

import pytest

from credit_risk.scorecard.woe import (
    SMOOTHING,
    bin_index,
    build_woe_table,
    quantile_cuts,
)


def test_quantile_cuts_splits_into_equal_count_groups():
    assert quantile_cuts(list(range(1, 11)), 2) == (6,)
    assert quantile_cuts(list(range(1, 11)), 5) == (3, 5, 7, 9)


def test_quantile_cuts_ignores_missing_and_removes_duplicates():
    assert quantile_cuts([None, 1, 1, 1, 1, 2, 2, 2, 2], 4) == (2,)  # 1 is the minimum, so no cut there
    assert quantile_cuts([4.0, 4.0, 4.0], 3) == ()  # constant ratio: one bin, no empty bins


def test_quantile_cuts_rejects_bad_input():
    with pytest.raises(ValueError):
        quantile_cuts([1, 2, 3], 1)
    with pytest.raises(ValueError):
        quantile_cuts([None, None], 2)


def test_bin_index_handles_edges_and_missing():
    cuts = (2.5, 5.0)
    assert bin_index(1.0, cuts) == 0
    assert bin_index(2.5, cuts) == 1  # a cut value starts the next bin
    assert bin_index(9.0, cuts) == 2
    assert bin_index(None, cuts) is None


def test_build_woe_table_counts_and_woe_match_hand_calculation():
    values = [1.0, 2.0, 3.0, 4.0, None]
    labels = [0, 0, 1, 1, 1]
    table = build_woe_table(values, labels, cuts=(2.5,))

    low, high, missing = table.bins
    assert (low.good, low.bad) == (2, 0)
    assert (high.good, high.bad) == (0, 2)
    assert (missing.good, missing.bad) == (0, 1)

    good_total, bad_total, k = 2, 3, 3
    low_good = (2 + SMOOTHING) / (good_total + SMOOTHING * k)
    low_bad = (0 + SMOOTHING) / (bad_total + SMOOTHING * k)
    assert low.woe == pytest.approx(math.log(low_good / low_bad))
    assert low.woe > 0  # survivors-heavy bin is safer
    assert high.woe < 0  # failure-heavy bin is riskier


def test_information_value_matches_formula_and_is_positive():
    values = [1.0, 2.0, 3.0, 4.0, None]
    labels = [0, 0, 1, 1, 1]
    table = build_woe_table(values, labels, cuts=(2.5,))
    expected = 0.0
    k = len(table.bins)
    for b in table.bins:
        g = (b.good + SMOOTHING) / (2 + SMOOTHING * k)
        d = (b.bad + SMOOTHING) / (3 + SMOOTHING * k)
        expected += (g - d) * math.log(g / d)
    assert table.information_value == pytest.approx(expected)
    assert table.information_value > 0


def test_woe_for_maps_new_values_to_their_bin():
    table = build_woe_table([1.0, 2.0, 3.0, 4.0, None], [0, 0, 1, 1, 1], cuts=(2.5,))
    assert table.woe_for(1.5) == table.bins[0].woe
    assert table.woe_for(3.5) == table.bins[1].woe
    assert table.woe_for(None) == table.bins[2].woe


def test_bin_labels_are_readable():
    table = build_woe_table([1.0, 2.0, 3.0, 4.0, None], [0, 0, 1, 1, 1], cuts=(2.5,))
    assert [b.label for b in table.bins] == ["< 2.5", ">= 2.5", "missing"]


def test_no_cut_points_gives_one_value_bin_and_a_missing_bin():
    table = build_woe_table([1.0, 2.0, None], [0, 1, 0], cuts=())
    assert [b.label for b in table.bins] == ["all non-missing values", "missing"]


def test_build_woe_table_rejects_bad_input():
    with pytest.raises(ValueError, match="same length"):
        build_woe_table([1.0], [0, 1], cuts=())
    with pytest.raises(ValueError, match="0 or 1"):
        build_woe_table([1.0, 2.0], [0, 2], cuts=())
    with pytest.raises(ValueError, match="good and one bad"):
        build_woe_table([1.0, 2.0], [0, 0], cuts=())
