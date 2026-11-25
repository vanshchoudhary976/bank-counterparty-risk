from datetime import date

import pytest

from credit_risk.scorecard.validation import (
    EXPECTED_SIGNS,
    drop_one_year_sensitivity,
    migration_matrix,
    migration_row_shares,
    missed_failures,
    sign_mismatches,
)


def _good_coefficients():
    return {name: 0.5 * sign for name, sign in EXPECTED_SIGNS.items()}


def test_correct_signs_pass():
    assert sign_mismatches(_good_coefficients()) == []


def test_wrong_sign_and_zero_are_both_flagged():
    coefficients = _good_coefficients()
    coefficients["tier1_leverage"] = 0.4  # should be negative
    coefficients["roa_annualised"] = 0.0  # zero does not show the expected direction
    assert sorted(sign_mismatches(coefficients)) == ["roa_annualised", "tier1_leverage"]


def test_missing_coefficient_is_refused():
    coefficients = _good_coefficients()
    del coefficients["efficiency_ratio"]
    with pytest.raises(ValueError, match="efficiency_ratio"):
        sign_mismatches(coefficients)


def test_sensitivity_reports_the_largest_move_when_a_year_is_dropped():
    # Fake fit: the coefficient equals the mean of the inputs it was given, so dropping rows moves it.
    rows = [(2005, [1.0], 0), (2005, [1.0], 0), (2006, [5.0], 0), (2006, [5.0], 0)]

    def fit(z_rows, labels):
        return {"x": sum(r[0] for r in z_rows) / len(z_rows)}

    results = {r.year: r for r in drop_one_year_sensitivity(rows, ["x"], fit)}
    assert results[2005].max_abs_change == pytest.approx(2.0)  # full mean 3, without 2005 mean 5
    assert results[2006].max_abs_change == pytest.approx(2.0)  # without 2006 mean 1
    assert results[2005].sign_flips == ()


def test_sensitivity_reports_sign_flips():
    rows = [(2005, [3.0], 0), (2006, [-1.0], 0), (2007, [-1.0], 0)]

    def fit(z_rows, labels):
        return {"x": sum(r[0] for r in z_rows)}

    # Full sum is +1. Dropping 2005 leaves -2, which flips the sign.
    results = {r.year: r for r in drop_one_year_sensitivity(rows, ["x"], fit)}
    assert results[2005].sign_flips == ("x",)
    assert results[2006].sign_flips == ()  # without 2006 the sum is +2
    assert results[2007].sign_flips == ()


def test_migration_matrix_counts_moves():
    matrix = migration_matrix([(1, 1), (1, 2), (1, 2), (10, 9)])
    assert matrix[0][0] == 1 and matrix[0][1] == 2 and matrix[9][8] == 1
    assert sum(sum(row) for row in matrix) == 4


def test_migration_row_shares_handle_empty_rows():
    matrix = migration_matrix([(1, 1), (1, 2)])
    shares = migration_row_shares(matrix)
    assert shares[0] == pytest.approx(0.5)
    assert shares[1] is None


def test_migration_refuses_grade_outside_one_to_ten():
    with pytest.raises(ValueError):
        migration_matrix([(0, 1)])


def test_missed_failures_lists_only_failures_in_safest_grades():
    records = [
        (1, date(2011, 12, 31), 0.01, 1, 1),  # missed: failure in grade 1
        (2, date(2011, 12, 31), 0.20, 9, 1),  # caught
        (3, date(2011, 12, 31), 0.02, 2, 0),  # survivor, not a miss
        (4, date(2012, 12, 31), 0.03, 3, 1),  # missed
    ]
    missed = missed_failures(records)
    assert [m.cert for m in missed] == [1, 4]
    assert missed[0].probability == pytest.approx(0.01)
