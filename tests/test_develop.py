import math
import random
from datetime import date

import pytest

from credit_risk.scorecard.develop import format_development, run_development
from credit_risk.scorecard.labels import Observation
from credit_risk.scorecard.split import TEST, VALIDATION, DEVELOPMENT, Window


def _quarter_ends(window: Window):
    out = []
    for year in range(window.start.year, window.end.year + 1):
        for month, day in ((3, 31), (6, 30), (9, 30), (12, 31)):
            d = date(year, month, day)
            if window.start <= d <= window.end:
                out.append(d)
    return out


def _rows(window, banks, rng, label_shift=0.0):
    out = []
    for report_date in _quarter_ends(window):
        for b in range(banks):
            eq = rng.gauss(0.09, 0.02)
            t1 = rng.gauss(0.10, 0.02)
            al = rng.gauss(0.015, 0.005)
            roa = rng.gauss(0.008, 0.006)
            ltd = rng.gauss(0.85, 0.15)
            er = rng.gauss(0.65, 0.10)
            z = -2.5 - 50 * (eq - 0.09) - 30 * (t1 - 0.10) + 80 * (al - 0.015) - 120 * (roa - 0.008) \
                + 4 * (ltd - 0.85) + 4 * (er - 0.65) + label_shift
            label = 1 if rng.random() < 1 / (1 + math.exp(-z)) else 0
            out.append(Observation(
                cert=b + 1,
                report_date=report_date,
                features={"equity_to_assets": eq, "tier1_leverage": t1, "allowance_to_loans": al,
                          "roa_annualised": roa, "loans_to_deposits": ltd, "efficiency_ratio": er},
                label=label,
            ))
    return out


def _observations(seed=7):
    rng = random.Random(seed)
    dev = _rows(DEVELOPMENT, 100, rng, label_shift=-0.5)
    val = _rows(VALIDATION, 100, rng)
    # One impossible value in development, which winsorising must cap.
    dev[0].features["loans_to_deposits"] = 5000.0
    return dev + val


@pytest.fixture(scope="module")
def results():
    return run_development(_observations())


def test_signs_match_the_economics(results):
    assert results.sign_problems == []


def test_validation_discrimination_is_above_chance(results):
    assert results.val_auc > 0.6
    assert results.val_gini == pytest.approx(2 * results.val_auc - 1)


def test_caps_come_from_development_and_limit_the_outlier(results):
    low, high = results.caps["loans_to_deposits"]
    assert high < 5000.0


def test_calibration_slope_is_positive(results):
    assert results.calibrator.slope > 0


def test_master_scale_has_nine_cut_offs(results):
    assert len(results.cutoffs) == 9


def test_sensitivity_has_one_row_per_development_year(results):
    assert [s.year for s in results.sensitivity] == [2005, 2006, 2007, 2008, 2009, 2010]


def test_test_window_rows_do_not_change_the_result():
    rng = random.Random(11)
    test_rows = _rows(TEST, 20, rng, label_shift=3.0)  # deliberately different, to prove they are ignored
    base = run_development(_observations())
    with_test = run_development(_observations() + test_rows)
    assert with_test.coefficients == base.coefficients
    assert with_test.val_auc == base.val_auc


def test_refuses_when_development_has_too_few_failures():
    obs = [o for o in _observations() if not DEVELOPMENT.contains(o.report_date)]
    dev = [Observation(o.cert, o.report_date, o.features, 0) for o in _observations() if DEVELOPMENT.contains(o.report_date)]
    with pytest.raises(ValueError, match="failures"):
        run_development(dev + obs)


def test_refuses_when_development_is_empty():
    obs = [o for o in _observations() if VALIDATION.contains(o.report_date)]
    with pytest.raises(ValueError):
        run_development(obs)


def test_format_names_the_test_set_as_unread(results):
    text = format_development(results)
    assert "Test set not read" in text
    assert "Rule 5 caps" in text
