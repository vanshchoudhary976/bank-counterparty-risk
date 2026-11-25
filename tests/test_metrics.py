import pytest

from credit_risk.scorecard.metrics import (
    decile_table,
    gini,
    ks_statistic,
    psi,
    riskiest_overlap,
    share_of_failures_in_riskiest_decile,
    spearman,
)


def test_perfect_separation_gives_ks_one_and_gini_one():
    scores = [0.9, 0.8, 0.2, 0.1]
    labels = [1, 1, 0, 0]
    assert ks_statistic(scores, labels) == pytest.approx(1.0)
    assert gini(scores, labels) == pytest.approx(1.0)


def test_ties_give_no_separation():
    scores = [0.5, 0.5, 0.5, 0.5]
    labels = [1, 0, 1, 0]
    assert ks_statistic(scores, labels) == pytest.approx(0.0)
    assert gini(scores, labels) == pytest.approx(0.0)


def test_ks_matches_hand_calculation():
    # Riskiest first: 0.9 (fail), 0.7 (survive), 0.6 (fail), 0.1 (survive).
    # After 0.9: failures 1/2 = 0.5, survivors 0/2 = 0 -> gap 0.5. After 0.7: 0.5 vs 0.5 -> 0.
    # After 0.6: 1.0 vs 0.5 -> gap 0.5. Largest gap is 0.5.
    assert ks_statistic([0.9, 0.7, 0.6, 0.1], [1, 0, 1, 0]) == pytest.approx(0.5)


def test_ks_refuses_one_class():
    with pytest.raises(ValueError):
        ks_statistic([0.1, 0.2], [0, 0])


def test_decile_table_counts_and_shares():
    pds = [i / 10 for i in range(10)]  # 0.0 to 0.9, one per decile
    labels = [1 if i >= 8 else 0 for i in range(10)]  # the two riskiest fail
    rows = decile_table(pds, labels)
    assert [r.count for r in rows] == [1] * 10
    assert rows[0].decile == 1 and rows[0].failures == 1 and rows[0].mean_predicted == pytest.approx(0.9)
    assert rows[1].failures == 1
    assert share_of_failures_in_riskiest_decile(rows) == pytest.approx(0.5)


def test_decile_table_needs_enough_rows():
    with pytest.raises(ValueError):
        decile_table([0.1, 0.2], [0, 1], deciles=10)


def test_psi_is_zero_for_identical_samples():
    values = [float(i) for i in range(100)]
    assert psi(values, values) == pytest.approx(0.0, abs=1e-9)


def test_psi_is_large_for_a_shifted_sample():
    expected = [float(i) for i in range(100)]
    actual = [float(i) + 50 for i in range(100)]
    assert psi(expected, actual) > 0.25


def test_spearman_is_one_for_same_order_and_minus_one_for_reversed():
    a = [1.0, 2.0, 3.0, 4.0]
    assert spearman(a, [10.0, 20.0, 30.0, 40.0]) == pytest.approx(1.0)
    assert spearman(a, [40.0, 30.0, 20.0, 10.0]) == pytest.approx(-1.0)


def test_spearman_refuses_constant_scores():
    with pytest.raises(ValueError):
        spearman([1.0, 1.0, 1.0], [1.0, 2.0, 3.0])


def test_riskiest_overlap_full_and_partial():
    a = [0.9, 0.8, 0.1, 0.2]
    assert riskiest_overlap(a, a, share=0.5) == pytest.approx(1.0)
    b = [0.1, 0.2, 0.9, 0.8]  # riskiest two are the other pair
    assert riskiest_overlap(a, b, share=0.5) == pytest.approx(0.0)
