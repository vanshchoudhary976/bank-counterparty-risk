import pytest

from credit_risk.exposure.measures import (
    LGD_BASE,
    LGD_SENSITIVITY,
    PD_FLOOR,
    concentration,
    expected_loss_rows,
    pd_for_grade,
    wrong_way_pfe,
)
from credit_risk.exposure.portfolio import Counterparty, Trade


def _t(kind, notional=1e6, cert=1, tid="1-1"):
    return Trade(trade_id=tid, cert=cert, kind=kind, notional=notional, maturity_years=2.0,
                 netting_set=str(cert), collateralised=kind == "REPO", direction=1)


def test_concentration_single_name_is_full_hhi_and_top5_one():
    c = concentration({1: 100.0})
    assert c["top5_share"] == pytest.approx(1.0)
    assert c["hhi"] == pytest.approx(10_000)


def test_concentration_equal_split_of_ten_gives_hhi_one_thousand():
    c = concentration({i: 1.0 for i in range(10)})
    assert c["hhi"] == pytest.approx(1_000)
    assert c["top5_share"] == pytest.approx(0.5)


def test_concentration_ignores_zero_exposures():
    assert concentration({1: 0.0, 2: 0.0}) == {"top5_share": 0.0, "hhi": 0.0}


def test_pd_has_floor_and_grade_ten_is_observed():
    assert pd_for_grade(1) == PD_FLOOR
    assert pd_for_grade(10) == pytest.approx(457 / 6822)
    with pytest.raises(ValueError):
        pd_for_grade(0)


def test_expected_loss_is_ead_times_pd_times_lgd():
    cps = [Counterparty(cert=1, name="A", grade=10)]
    (row,) = expected_loss_rows(cps, {1: 1_000_000.0})
    assert row[4][LGD_BASE] == pytest.approx(1_000_000.0 * (457 / 6822) * LGD_BASE)
    assert row[4][LGD_SENSITIVITY[0]] < row[4][LGD_SENSITIVITY[-1]]


def test_wrong_way_raises_peak_when_repo_present():
    from credit_risk.exposure.measures import WRONG_WAY_FACTOR, uncollateralised_peak
    from credit_risk.exposure.limits import counterparty_pfe

    trades = [_t("REPO"), _t("DEPOSIT", tid="1-2")]
    base = float(counterparty_pfe(trades).max())
    assert wrong_way_pfe(trades) == pytest.approx(base * WRONG_WAY_FACTOR)


def test_wrong_way_unchanged_without_repo():
    from credit_risk.exposure.limits import counterparty_pfe

    trades = [_t("DEPOSIT"), _t("FX_FORWARD", tid="1-2")]
    assert wrong_way_pfe(trades) == pytest.approx(float(counterparty_pfe(trades).max()))
