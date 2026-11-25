import pytest

from credit_risk.exposure.limits import (
    CAPITAL_BASE,
    build_limit_rows,
    format_limits,
    limit_for_grade,
    status,
    utilisation,
)
from credit_risk.exposure.portfolio import Counterparty, Trade


def test_limit_falls_with_grade_and_grade_ten_is_zero():
    assert limit_for_grade(1) > limit_for_grade(4) > limit_for_grade(8) > limit_for_grade(10)
    assert limit_for_grade(10) == 0


def test_bad_grade_rejected():
    with pytest.raises(ValueError):
        limit_for_grade(11)


def test_status_bands_boundaries():
    assert status(0.79) == "green"
    assert status(0.80) == "amber"
    assert status(1.00) == "amber"
    assert status(1.01) == "red"


def test_utilisation_is_peak_over_limit():
    assert utilisation(50.0, 100.0) == 0.5


def test_zero_limit_with_exposure_is_red_and_without_is_green():
    assert utilisation(10.0, 0.0) == float("inf")
    assert status(utilisation(10.0, 0.0)) == "red"
    assert status(utilisation(0.0, 0.0)) == "green"


def _trade(cert, kind, notional, tid, maturity=2.0):
    return Trade(trade_id=tid, cert=cert, kind=kind, notional=notional, maturity_years=maturity,
                 netting_set=str(cert), collateralised=kind in ("IRS", "REPO"), direction=1)


def test_breach_report_names_counterparty_and_flags_red():
    big = CAPITAL_BASE * 0.5  # far above a grade 8 limit of 1% of capital
    cps = [Counterparty(cert=1, name="Big bank", grade=8), Counterparty(cert=2, name="Small bank", grade=1)]
    trades = [_trade(1, "DEPOSIT", big, "1-1"), _trade(2, "DEPOSIT", 1_000.0, "2-1")]
    rows = {r.cert: r for r in build_limit_rows(cps, trades, paths=200, seed=3)}
    assert rows[1].status == "red"
    assert rows[1].drivers and rows[1].drivers[0].startswith("1-1")
    assert rows[2].status == "green"
    text = format_limits(list(rows.values()))
    assert "Big bank" in text and "Breach report: 1 counterparties above 100%" in text


def test_grade_ten_with_exposure_is_flagged_reduce_only():
    cps = [Counterparty(cert=5, name="Weak bank", grade=10)]
    trades = [_trade(5, "DEPOSIT", 1_000_000.0, "5-1")]
    (row,) = build_limit_rows(cps, trades, paths=200, seed=3)
    assert row.status == "red"
    assert "reduce-only" in row.action
