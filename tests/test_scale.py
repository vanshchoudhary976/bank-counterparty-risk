import math

import pytest

from credit_risk.scorecard.scale import MasterScale, ScoreScale, training_quantile_cutoffs

CUTS = (0.001, 0.003, 0.006, 0.01, 0.02, 0.04, 0.08, 0.15, 0.3)


def test_score_equals_base_score_at_base_odds():
    scale = ScoreScale(base_score=600, base_odds=50, pdo=20)
    pd = 1 / 51  # 50 survivors per failure
    assert scale.score(pd) == pytest.approx(600)


def test_doubling_good_odds_adds_pdo_points():
    scale = ScoreScale(base_score=600, base_odds=50, pdo=20)
    higher = scale.score(1 / 101)  # good odds 100:1, double the base 50:1
    assert higher - 600 == pytest.approx(20)


def test_riskier_bank_gets_lower_score():
    scale = ScoreScale()
    assert scale.score(0.01) > scale.score(0.10)


def test_score_stays_finite_at_extreme_pd():
    scale = ScoreScale()
    assert math.isfinite(scale.score(0.0))
    assert math.isfinite(scale.score(1.0))


def test_score_scale_rejects_bad_input():
    with pytest.raises(ValueError):
        ScoreScale(base_odds=0)
    with pytest.raises(ValueError):
        ScoreScale().score(1.5)


def test_master_scale_grade_boundaries():
    scale = MasterScale(CUTS)
    assert scale.grade(0.0) == 1
    assert scale.grade(0.001) == 1  # a value on the cut-off stays in the lower grade
    assert scale.grade(0.0011) == 2
    assert scale.grade(0.3) == 9
    assert scale.grade(0.31) == 10
    assert scale.grade(1.0) == 10


def test_master_scale_is_monotonic_in_pd():
    scale = MasterScale(CUTS)
    grades = [scale.grade(p / 1000) for p in range(0, 1001)]
    assert grades == sorted(grades)
    assert set(grades) == set(range(1, 11))


def test_master_scale_rejects_wrong_number_of_cutoffs():
    with pytest.raises(ValueError, match="9 cut-offs"):
        MasterScale(CUTS[:-1])


def test_master_scale_rejects_unsorted_or_out_of_range_cutoffs():
    with pytest.raises(ValueError, match="must not decrease"):
        MasterScale((0.2,) + CUTS[1:])
    with pytest.raises(ValueError, match="between 0 and 1"):
        MasterScale(CUTS[:-1] + (1.0,))


def test_training_cutoffs_give_about_equal_grade_sizes():
    pds = [i / 1000 for i in range(1, 1001)]  # 1000 banks with PDs 0.001 to 1.000
    cutoffs = training_quantile_cutoffs(pds)
    assert len(cutoffs) == 9
    scale = MasterScale(cutoffs)
    counts = [0] * 10
    for pd in pds:
        counts[scale.grade(pd) - 1] += 1
    assert all(abs(c - 100) <= 2 for c in counts), counts


def test_training_cutoffs_keep_ties_and_leave_grades_empty():
    cutoffs = training_quantile_cutoffs([0.05] * 100)
    assert cutoffs == (0.05,) * 9
    scale = MasterScale(cutoffs)
    assert scale.grade(0.05) == 1  # every bank sits at the first cut-off, so grades 2 to 9 stay empty
    assert scale.grade(0.06) == 10
