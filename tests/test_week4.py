import math
import random
from datetime import date

import pytest

from credit_risk.config import ProjectPaths
from credit_risk.scorecard import week4
from credit_risk.scorecard.labels import Observation
from credit_risk.scorecard.split import CASE_STUDY, DEVELOPMENT, TEST, VALIDATION
from credit_risk.scorecard.week4 import format_week4, main, run_week4


def _quarter_ends(window):
    out = []
    for year in range(window.start.year, window.end.year + 1):
        for month, day in ((3, 31), (6, 30), (9, 30), (12, 31)):
            d = date(year, month, day)
            if window.start <= d <= window.end:
                out.append(d)
    return out


def _observations(seed=7, banks=(125, 125, 50, 100)):
    """Synthetic bank-quarters with the economically expected signs.

    Each window is a full panel: the same banks report every quarter-end, so one-year migration
    pairs exist. Some ratios are missing on purpose, to test the complete-case rule.
    """
    rng = random.Random(seed)
    out = []
    for window_index, (window, n_banks) in enumerate(zip((DEVELOPMENT, VALIDATION, TEST, CASE_STUDY), banks)):
        for report_date in _quarter_ends(window):
            for b in range(n_banks):
                cert = 10000 * (window_index + 1) + b
                eq = rng.gauss(0.09, 0.02)
                t1 = rng.gauss(0.10, 0.02)
                al = rng.gauss(0.015, 0.005)
                roa = rng.gauss(0.008, 0.006)
                ltd = rng.gauss(0.85, 0.15)
                er = rng.gauss(0.65, 0.10)
                z = -2.5 - 50 * (eq - 0.09) - 30 * (t1 - 0.10) + 80 * (al - 0.015) - 120 * (roa - 0.008) \
                    + 4 * (ltd - 0.85) + 4 * (er - 0.65)
                label = 1 if rng.random() < 1 / (1 + math.exp(-z)) else 0
                features = {
                    "equity_to_assets": eq,
                    "tier1_leverage": t1,
                    "allowance_to_loans": al,
                    "roa_annualised": roa,
                    "loans_to_deposits": ltd,
                    "efficiency_ratio": er,
                }
                if rng.random() < 0.02:
                    features["equity_to_assets"] = None
                out.append(Observation(cert, report_date, features, label))
    return out


@pytest.fixture(scope="module")
def results():
    return run_week4(_observations())


def test_coefficient_signs_match_the_economics(results):
    assert results.sign_problems == []


def test_test_set_discrimination_is_above_chance(results):
    assert results.test.auc > 0.6
    assert results.test.gini == pytest.approx(2 * results.test.auc - 1)


def test_calibration_slope_is_positive(results):
    assert results.calibrator.slope > 0


def test_master_scale_has_ten_grades_and_separates_the_extremes(results):
    assert len(results.cutoffs) == 9
    riskiest = results.grade_rows_test[-1]
    safest = results.grade_rows_test[0]
    assert riskiest.failure_rate > 3 * safest.failure_rate


def test_no_input_shows_a_major_shift_between_development_and_test(results):
    assert all(v < 0.25 for v in results.psi_by_input.values())


def test_sensitivity_has_one_row_per_development_year(results):
    assert [s.year for s in results.sensitivity] == [2005, 2006, 2007, 2008, 2009, 2010]


def test_incomplete_rows_are_dropped_and_counted(results):
    assert results.dropped_incomplete["development"] > 0
    assert results.dropped_incomplete["test"] > 0


def test_benchmarks_are_in_range(results):
    for value in results.benchmark_auc_test.values():
        assert 0.0 <= value <= 1.0
    assert -1.0 <= results.spearman_model_expert <= 1.0
    assert 0.0 <= results.overlap_model_expert <= 1.0


def test_migration_counts_are_non_negative_and_cover_the_test_set(results):
    total = sum(sum(row) for row in results.migration)
    assert total > 0
    assert all(v >= 0 for row in results.migration for v in row)


def test_case_study_is_scored_with_the_frozen_model(results):
    assert len(results.case_study) > 0
    assert all(1 <= c.grade <= 10 for c in results.case_study)
    assert all(0.0 < c.pd < 1.0 for c in results.case_study)


def test_report_states_the_limitations(results):
    text = format_week4(results)
    assert "Week 4" in text
    assert "Limitations" in text
    assert "NOT done" in text
    assert "not an IFRS 9 or regulatory rating" in text


def test_refuses_when_development_is_empty():
    observations = [o for o in _observations() if o.report_date.year >= 2011]
    with pytest.raises(ValueError):
        run_week4(observations)


def test_refuses_when_development_has_too_few_events():
    observations = []
    for o in _observations():
        if DEVELOPMENT.contains(o.report_date):
            o = Observation(o.cert, o.report_date, o.features, 0)
        observations.append(o)
    with pytest.raises(ValueError):
        run_week4(observations)


def test_marker_stops_a_second_scoring_run(tmp_path, monkeypatch, capsys):
    (tmp_path / "reports").mkdir()
    (tmp_path / "reports" / week4.MARKER_NAME).write_text("2026-11-22T10:00:00\n", encoding="utf-8")
    monkeypatch.setattr(ProjectPaths, "default", classmethod(lambda cls: ProjectPaths(root=tmp_path)))
    assert main([]) == 1
    assert "used once" in capsys.readouterr().out
