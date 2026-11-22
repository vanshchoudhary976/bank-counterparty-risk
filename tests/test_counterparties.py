from datetime import date

import pytest

from credit_risk.exposure.counterparties import (
    MIN_TOTAL_ASSETS,
    eligible_certs,
    fit_grader,
    grade_counterparties,
    select_certs,
)
from credit_risk.scorecard.labels import Observation
from credit_risk.scorecard.panel import RATIO_COLUMNS


def test_eligible_keeps_only_banks_above_floor_and_sorts():
    assets = {3: MIN_TOTAL_ASSETS * 2, 1: MIN_TOTAL_ASSETS / 2, 2: MIN_TOTAL_ASSETS, 4: None}  # thousands of dollars
    assert eligible_certs(assets) == [2, 3]


def test_select_is_reproducible_and_sized():
    certs = list(range(100, 130))
    a = select_certs(certs, count=12, seed=42)
    assert a == select_certs(certs, count=12, seed=42)
    assert len(a) == 12 and len(set(a)) == 12
    assert a == sorted(a)


def test_select_rejects_too_few_banks():
    with pytest.raises(ValueError):
        select_certs(list(range(5)), count=12)


def test_select_rejects_bad_count():
    with pytest.raises(ValueError):
        select_certs(list(range(30)), count=3)


def _synthetic_observations():
    """Bank-quarters in 2005 to 2013 with a simple risk signal, so the grader can fit."""
    import random

    rnd = random.Random(1)
    obs = []
    for cert in range(1, 401):
        for year in range(2005, 2014):
            for q in (3, 6, 9, 12):
                d = date(year, q, 28 if q == 2 else 30)
                risk = rnd.random()
                feats = {n: rnd.gauss(0, 1) for n in RATIO_COLUMNS}
                feats["tier1_leverage"] = 0.10 - 0.05 * risk
                feats["equity_to_assets"] = 0.10 - 0.05 * risk
                label = 1 if risk > 0.97 else 0
                obs.append(Observation(cert=cert, report_date=d, features=feats, label=label))
    return obs


def test_grader_returns_grade_between_one_and_ten():
    obs = _synthetic_observations()
    feats = dict(obs[0].features)
    rows = [{"cert": 1, "name": "Test bank 1", "features": feats}]
    result = grade_counterparties(obs, rows)
    assert len(result) == 1 and 1 <= result[0].grade <= 10


def test_grader_rejects_empty_development():
    with pytest.raises(ValueError):
        fit_grader([])
