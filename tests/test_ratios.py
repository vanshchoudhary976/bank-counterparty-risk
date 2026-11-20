from datetime import date
from pathlib import Path

import pytest

from credit_risk.ratios import (
    equity_to_assets,
    loans_to_deposits,
    months_in_period,
    ratios_for_row,
    roa_annualised,
    roa_ytd,
    safe_divide,
)

SQL_FILE = Path(__file__).resolve().parents[1] / "sql" / "03_ratios.sql"


def test_safe_divide_returns_none_for_missing_input():
    assert safe_divide(None, 10.0) is None
    assert safe_divide(10.0, None) is None


def test_safe_divide_returns_none_for_zero_denominator():
    assert safe_divide(10.0, 0.0) is None


def test_safe_divide_divides_normally():
    assert safe_divide(1.0, 4.0) == pytest.approx(0.25)


def test_equity_to_assets():
    assert equity_to_assets(100.0, 1000.0) == pytest.approx(0.10)


def test_loans_to_deposits():
    assert loans_to_deposits(600.0, 800.0) == pytest.approx(0.75)


def test_roa_ytd_is_not_scaled():
    assert roa_ytd(5.0, 1000.0) == pytest.approx(0.005)


def test_months_in_period_reads_the_report_month():
    assert months_in_period(date(2026, 6, 30)) == 6
    assert months_in_period(date(2022, 12, 31)) == 12
    assert months_in_period(date(2023, 3, 31)) == 3


def test_annualised_june_doubles_the_six_month_figure():
    # 5 of six-month income on 1000 of assets = 0.5% year to date, so 1.0% a year.
    assert roa_annualised(5.0, 1000.0, months=6) == pytest.approx(0.01)


def test_annualised_december_leaves_the_figure_unchanged():
    assert roa_annualised(5.0, 1000.0, months=12) == pytest.approx(0.005)


def test_annualised_quarter_multiplies_by_four():
    assert roa_annualised(5.0, 1000.0, months=3) == pytest.approx(0.02)


def test_annualised_rejects_impossible_month_counts():
    with pytest.raises(ValueError):
        roa_annualised(5.0, 1000.0, months=0)
    with pytest.raises(ValueError):
        roa_annualised(5.0, 1000.0, months=13)


def test_roa_annualised_is_none_when_assets_zero():
    assert roa_annualised(5.0, 0.0, months=6) is None


def test_ratios_for_row_bundles_every_ratio_for_a_june_report():
    r = ratios_for_row(1, date(2026, 6, 30), 1000.0, 100.0, 600.0, 800.0, 5.0)
    assert r.equity_to_assets == pytest.approx(0.10)
    assert r.loans_to_deposits == pytest.approx(0.75)
    assert r.roa_ytd == pytest.approx(0.005)
    assert r.roa_annualised == pytest.approx(0.01)


def test_ratios_for_row_gives_none_for_missing_inputs():
    r = ratios_for_row(1, date(2026, 6, 30), None, 100.0, 600.0, 800.0, 5.0)
    assert r.equity_to_assets is None
    assert r.roa_ytd is None
    assert r.roa_annualised is None
    assert r.loans_to_deposits == pytest.approx(0.75)


def test_sql_view_matches_python_and_handles_zero_assets(warehouse):
    warehouse.con.execute("INSERT INTO institutions VALUES (1, 'TEST BANK', 'NY', TRUE)")
    warehouse.con.execute(
        "INSERT INTO bank_financials VALUES "
        "(1, DATE '2023-03-31', 1000.0, 100.0, 600.0, 800.0, 5.0), "
        "(2, DATE '2023-03-31', 0.0, 100.0, 600.0, 800.0, 5.0), "
        "(3, DATE '2026-06-30', 1000.0, 100.0, 600.0, 800.0, 5.0), "
        "(4, DATE '2022-12-31', 1000.0, 100.0, 600.0, 800.0, 5.0)"
    )
    warehouse.apply_sql_file(SQL_FILE)

    rows = warehouse.con.execute(
        "SELECT cert, bank_name, equity_to_assets, loans_to_deposits, roa_ytd, roa_annualised "
        "FROM bank_ratios ORDER BY cert"
    ).fetchall()

    cert1, name1, eta1, ltd1, roay1, roaa1 = rows[0]
    assert cert1 == 1 and name1 == "TEST BANK"
    assert eta1 == pytest.approx(0.10)
    assert ltd1 == pytest.approx(0.75)
    assert roay1 == pytest.approx(0.005)
    assert roaa1 == pytest.approx(0.02)  # March: factor 4

    cert2, name2, eta2, ltd2, roay2, roaa2 = rows[1]
    assert cert2 == 2 and name2 is None
    assert eta2 is None and roay2 is None and roaa2 is None
    assert ltd2 == pytest.approx(0.75)

    cert3, _, _, _, roay3, roaa3 = rows[2]
    assert cert3 == 3
    assert roay3 == pytest.approx(0.005)
    assert roaa3 == pytest.approx(0.01)  # June: factor 2

    cert4, _, _, _, roay4, roaa4 = rows[3]
    assert cert4 == 4
    assert roay4 == pytest.approx(0.005)
    assert roaa4 == pytest.approx(0.005)  # December: factor 1
