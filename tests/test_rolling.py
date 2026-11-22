import math
import random
from datetime import date

import pytest

from credit_risk.scorecard.labels import Observation
from credit_risk.scorecard.rolling import format_rolling, run_rolling, score_year


def _quarter_ends(year):
    return [date(year, m, d) for m, d in ((3, 31), (6, 30), (9, 30), (12, 31))]


def _rows(year, banks, rng, shift=0.0):
    out = []
    for report_date in _quarter_ends(year):
        for b in range(banks):
            eq = rng.gauss(0.09, 0.02)
            t1 = rng.gauss(0.10, 0.02)
            al = rng.gauss(0.015, 0.005)
            roa = rng.gauss(0.008, 0.006)
            ltd = rng.gauss(0.85, 0.15)
            er = rng.gauss(0.65, 0.10)
            z = -2.5 - 50 * (eq - 0.09) - 30 * (t1 - 0.10) + 80 * (al - 0.015) - 120 * (roa - 0.008) \
                + 4 * (ltd - 0.85) + 4 * (er - 0.65) + shift
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
    obs = []
    for year in range(2005, 2014):
        obs += _rows(year, 100, rng, shift=-0.5)
    return obs


@pytest.fixture(scope="module")
def results():
    return run_rolling(_observations())


def test_three_years_are_scored(results):
    assert [r.year for r in results] == [2011, 2012, 2013]


def test_model_discriminates_above_chance(results):
    for r in results:
        assert r.model_auc > 0.6
        assert r.model_gini == pytest.approx(2 * r.model_auc - 1)


def test_training_grows_each_year(results):
    rows = [r.train_rows for r in results]
    assert rows == sorted(rows) and rows[0] < rows[-1]


def test_years_after_2013_do_not_change_the_result(results):
    rng = random.Random(99)
    later = []
    for year in (2014, 2015):
        later += _rows(year, 50, rng, shift=3.0)
    again = run_rolling(_observations() + later)
    assert [(r.model_auc, r.train_rows) for r in again] == [(r.model_auc, r.train_rows) for r in results]


def test_refuses_when_training_has_too_few_failures():
    obs = [Observation(o.cert, o.report_date, o.features, 0) for o in _observations() if o.report_date.year < 2011]
    obs += [o for o in _observations() if o.report_date.year == 2011]
    with pytest.raises(ValueError, match="failures"):
        score_year(obs, 2011)


def test_refuses_a_test_year_with_no_failures():
    obs = [o if o.report_date.year < 2011 else Observation(o.cert, o.report_date, o.features, 0)
           for o in _observations()]
    with pytest.raises(ValueError, match="both failures and survivors"):
        score_year(obs, 2011)


def test_format_lists_each_year(results):
    text = format_rolling(results)
    for year in (2011, 2012, 2013):
        assert str(year) in text
    assert "not the blueprint test gate" in text
