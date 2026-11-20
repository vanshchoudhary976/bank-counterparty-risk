import pytest

from credit_risk.scorecard.evaluation import auc, default_rate_by_grade, is_risk_ordered, GradeRow


def test_auc_is_one_when_every_failure_scores_riskier():
    assert auc([0.1, 0.2, 0.8, 0.9], [0, 0, 1, 1]) == pytest.approx(1.0)


def test_auc_is_zero_when_ranking_is_reversed():
    assert auc([0.9, 0.8, 0.2, 0.1], [0, 0, 1, 1]) == pytest.approx(0.0)


def test_auc_is_half_when_all_scores_tie():
    assert auc([0.5, 0.5, 0.5, 0.5], [0, 1, 0, 1]) == pytest.approx(0.5)


def test_auc_matches_hand_count_of_pairs():
    # Failures: 0.35 and 0.8. Survivors: 0.1 and 0.4.
    # Pairs where the failure scores higher: (0.35, 0.1), (0.8, 0.1), (0.8, 0.4). Not (0.35, 0.4).
    assert auc([0.1, 0.4, 0.35, 0.8], [0, 0, 1, 1]) == pytest.approx(0.75)


def test_auc_rejects_missing_class():
    with pytest.raises(ValueError, match="both failures and survivors"):
        auc([0.1, 0.2], [0, 0])


def test_default_rate_by_grade_counts_failures_per_grade():
    rows = default_rate_by_grade([1, 1, 2, 2, 2], [0, 1, 0, 0, 1])
    assert rows == [
        GradeRow(grade=1, count=2, failures=1, failure_rate=0.5),
        GradeRow(grade=2, count=3, failures=1, failure_rate=1 / 3),
    ]


def test_is_risk_ordered_detects_rising_failure_rates():
    rising = [GradeRow(1, 10, 0, 0.0), GradeRow(2, 10, 1, 0.1), GradeRow(3, 10, 3, 0.3)]
    falling = list(reversed(rising))
    assert is_risk_ordered(rising)
    assert not is_risk_ordered(falling)
