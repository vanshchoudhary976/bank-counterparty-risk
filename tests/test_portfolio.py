from pathlib import Path

import pytest

from credit_risk.exposure.portfolio import (
    MAX_MATURITY_YEARS,
    MIN_MATURITY_YEARS,
    Counterparty,
    generate_portfolio,
    read_portfolio,
    write_portfolio,
)


def _cps(n: int = 12) -> list[Counterparty]:
    return [Counterparty(cert=1000 + i, name=f"Test bank {i}", grade=(i % 10) + 1) for i in range(n)]


def test_trade_count_per_counterparty_is_between_two_and_four():
    trades = generate_portfolio(_cps())
    for cert in {t.cert for t in trades}:
        assert 2 <= sum(1 for t in trades if t.cert == cert) <= 4


def test_same_seed_gives_identical_portfolio():
    assert generate_portfolio(_cps(), seed=7) == generate_portfolio(_cps(), seed=7)


def test_different_seed_changes_portfolio():
    assert generate_portfolio(_cps(), seed=7) != generate_portfolio(_cps(), seed=8)


def test_maturities_and_notionals_are_in_range():
    for t in generate_portfolio(_cps()):
        assert MIN_MATURITY_YEARS <= t.maturity_years <= MAX_MATURITY_YEARS
        assert t.notional > 0


def test_netting_set_is_one_per_counterparty():
    trades = generate_portfolio(_cps())
    for t in trades:
        assert t.netting_set == str(t.cert)


def test_only_irs_and_repo_are_collateralised():
    for t in generate_portfolio(_cps()):
        assert t.collateralised == (t.kind in ("IRS", "REPO"))


def test_too_few_counterparties_rejected():
    with pytest.raises(ValueError):
        generate_portfolio(_cps(11))


def test_too_many_counterparties_rejected():
    with pytest.raises(ValueError):
        generate_portfolio(_cps(16))


def test_duplicate_cert_rejected():
    cps = _cps()
    cps[1] = Counterparty(cert=cps[0].cert, name="dup", grade=1)
    with pytest.raises(ValueError):
        generate_portfolio(cps)


def test_grade_out_of_range_rejected():
    cps = _cps()
    cps[0] = Counterparty(cert=cps[0].cert, name="bad", grade=11)
    with pytest.raises(ValueError):
        generate_portfolio(cps)


def test_csv_round_trip_keeps_trades(tmp_path: Path):
    trades = generate_portfolio(_cps())
    path = tmp_path / "portfolio_assumptions.csv"
    write_portfolio(trades, path)
    back = read_portfolio(path)
    assert [t.trade_id for t in back] == [t.trade_id for t in trades]
    assert all(abs(a.notional - b.notional) < 1 for a, b in zip(back, trades))
    assert [t.collateralised for t in back] == [t.collateralised for t in trades]


def test_csv_without_illustrative_label_is_rejected(tmp_path: Path):
    path = tmp_path / "p.csv"
    write_portfolio(generate_portfolio(_cps()), path)
    path.write_text(path.read_text().replace("ILLUSTRATIVE", "REAL", 1))
    with pytest.raises(ValueError):
        read_portfolio(path)


def test_direction_is_plus_or_minus_one_and_lending_is_positive():
    for t in generate_portfolio(_cps()):
        assert t.direction in (1, -1)
        if t.kind in ("DEPOSIT", "REPO"):
            assert t.direction == 1
