"""Tests for Module D step 3: expected loss and exposure under stress."""

import pytest

from credit_risk.exposure.measures import DOWNGRADE_GRADES, LGD_BASE, PD_FLOOR, WRONG_WAY_FACTOR, pd_for_grade
from credit_risk.stress.expected_loss import (
    StressRow,
    build_row,
    expected_loss,
    format_expected_loss,
    grade_downgrade,
    scenario_totals,
    stressed_ead,
)


def test_expected_loss_is_ead_times_pd_times_lgd():
    assert expected_loss(100.0, 0.02, 0.5) == pytest.approx(1.0)


def test_expected_loss_is_zero_when_pd_is_zero():
    assert expected_loss(1_000.0, 0.0) == 0.0


def test_expected_loss_default_lgd_is_base_lgd():
    assert expected_loss(100.0, 0.1) == pytest.approx(100.0 * 0.1 * LGD_BASE)


@pytest.mark.parametrize(
    "ead, pd, lgd",
    [(-1.0, 0.1, 0.45), (100.0, -0.01, 0.45), (100.0, 1.01, 0.45), (100.0, 0.1, 1.5)],
)
def test_expected_loss_rejects_out_of_range_inputs(ead, pd, lgd):
    with pytest.raises(ValueError):
        expected_loss(ead, pd, lgd)


def test_grade_downgrade_counts_moves_towards_grade_10():
    assert grade_downgrade(3, 5) == 2
    assert grade_downgrade(5, 3) == -2


def test_grade_downgrade_rejects_grades_outside_1_to_10():
    with pytest.raises(ValueError):
        grade_downgrade(0, 5)
    with pytest.raises(ValueError):
        grade_downgrade(5, 11)


def test_stressed_ead_unchanged_without_repo():
    assert stressed_ead(1_000.0, 3, 9, has_repo=False) == 1_000.0


def test_stressed_ead_unchanged_for_small_downgrade_with_repo():
    assert stressed_ead(1_000.0, 3, 3 + DOWNGRADE_GRADES - 1, has_repo=True) == 1_000.0


def test_stressed_ead_scaled_for_repo_downgraded_by_threshold():
    assert stressed_ead(1_000.0, 3, 3 + DOWNGRADE_GRADES, has_repo=True) == pytest.approx(
        1_000.0 * WRONG_WAY_FACTOR
    )


def test_stressed_ead_rejects_negative_base():
    with pytest.raises(ValueError):
        stressed_ead(-1.0, 3, 5, has_repo=True)


def test_build_row_uses_grade_pds_and_increases_loss_when_grade_moves_to_10():
    row = build_row(1, "Bank A", "Credit shock", 3, 10, base_ead=1_000_000.0, has_repo=False)
    assert row.base_pd == pd_for_grade(3)
    assert row.stressed_pd == pd_for_grade(10)
    assert row.base_el == pytest.approx(1_000_000.0 * pd_for_grade(3) * LGD_BASE)
    assert row.stressed_el == pytest.approx(1_000_000.0 * pd_for_grade(10) * LGD_BASE)
    assert row.el_change > 0


def test_pd_floor_binds_for_grades_1_to_9():
    # Grades 1 to 9 have validation default rates below the floor, so the floor sets their PD.
    # Moves between these grades change no expected loss. This is a documented limitation.
    for grade in range(1, 10):
        assert pd_for_grade(grade) == PD_FLOOR
    assert pd_for_grade(10) > PD_FLOOR


def test_build_row_el_change_is_stressed_minus_base():
    row = StressRow(1, "A", "S", 3, 6, 0.01, 0.02, 100.0, 150.0, 0.5, 1.5)
    assert row.el_change == pytest.approx(1.0)


def test_build_row_applies_wrong_way_exposure_for_repo_downgrade():
    row = build_row(1, "Bank A", "Combined", 2, 4, base_ead=1_000_000.0, has_repo=True)
    assert row.stressed_ead == pytest.approx(1_000_000.0 * WRONG_WAY_FACTOR)


def test_scenario_totals_sum_each_scenario_separately():
    rows = [
        build_row(1, "A", "Credit shock", 3, 6, 100.0, False),
        build_row(2, "B", "Credit shock", 2, 5, 200.0, False),
        build_row(1, "A", "Rate shock", 3, 4, 100.0, False),
    ]
    totals = scenario_totals(rows)
    assert set(totals) == {"Credit shock", "Rate shock"}
    base, stressed, change = totals["Credit shock"]
    assert base == pytest.approx(rows[0].base_el + rows[1].base_el)
    assert stressed == pytest.approx(rows[0].stressed_el + rows[1].stressed_el)
    assert change == pytest.approx(stressed - base)


def test_format_is_labelled_illustrative_and_lists_each_scenario():
    rows = [
        build_row(1, "Bank A", "Credit shock", 3, 6, 100.0, False),
        build_row(1, "Bank A", "Rate shock", 3, 4, 100.0, False),
    ]
    text = format_expected_loss(rows)
    assert "ILLUSTRATIVE" in text
    assert "Credit shock" in text and "Rate shock" in text
    assert "Totals by scenario" in text
    assert "Bank A (cert 1)" in text
