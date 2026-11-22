from datetime import date
from pathlib import Path

import duckdb
import pytest

SQL_DIR = Path(__file__).resolve().parents[1] / "sql"


@pytest.fixture()
def con():
    db = duckdb.connect(":memory:")
    for name in ("01_schema.sql", "03_ratios.sql", "05_analysis.sql"):
        db.execute((SQL_DIR / name).read_text(encoding="utf-8"))
    db.execute("INSERT INTO institutions VALUES (1, 'Small Bank', 'NY', TRUE), (2, 'Mid Bank', 'CA', TRUE)")
    # Cert 1: $500m assets, 4% equity, loans below deposits, net income 1,000 in June (annualised x2).
    # Cert 2: $5bn assets, 10% equity, loans above deposits.
    db.execute(
        """
        INSERT INTO bank_financials VALUES
        (1, DATE '2010-12-31', 500000, 20000, 300000, 400000, 4000),
        (2, DATE '2010-12-31', 5000000, 500000, 6000000, 4000000, 50000),
        (1, DATE '2011-06-30', 500000, 20000, 300000, 400000, 1000)
        """
    )
    # Cert 1 fails in March 2011, so its last report before failure is 2010-12-31.
    db.execute("INSERT INTO bank_failures VALUES (1, 'Small Bank', DATE '2011-03-15'), (NULL, 'No Cert', DATE '2011-05-01')")
    yield db
    db.close()


def test_size_bands_follow_total_assets(con):
    rows = dict(con.execute(
        "SELECT cert, size_band FROM peer_group_quarters WHERE report_date = DATE '2010-12-31'"
    ).fetchall())
    assert rows == {1: "a: under $1bn", 2: "b: $1bn to $10bn"}


def test_median_equity_to_assets_by_band(con):
    rows = con.execute(
        "SELECT size_band, median_equity_to_assets FROM analysis_equity_to_assets_by_band WHERE report_year = 2010"
    ).fetchall()
    result = dict(rows)
    assert result["a: under $1bn"] == pytest.approx(0.04)
    assert result["b: $1bn to $10bn"] == pytest.approx(0.10)


def test_share_of_loans_above_deposits_by_band(con):
    result = dict(con.execute(
        "SELECT size_band, share_loans_above_deposits FROM analysis_loans_above_deposits_by_band WHERE report_year = 2010"
    ).fetchall())
    assert result["a: under $1bn"] == pytest.approx(0.0)
    assert result["b: $1bn to $10bn"] == pytest.approx(1.0)


def test_roa_uses_annualised_figure(con):
    result = dict(con.execute(
        "SELECT report_year, median_roa_annualised FROM analysis_roa_by_band_year WHERE size_band = 'a: under $1bn'"
    ).fetchall())
    # 2010: 4,000 / 500,000 = 0.008. 2011 June: 1,000 / 500,000 x 2 = 0.004.
    assert result[2010] == pytest.approx(0.008)
    assert result[2011] == pytest.approx(0.004)


def test_failures_are_placed_in_band_of_last_report(con):
    rows = con.execute("SELECT fail_year, size_band, failures FROM analysis_failures_by_band_year").fetchall()
    assert rows == [(2011, "a: under $1bn", 1)]


def test_low_capital_latest_lists_only_banks_under_five_percent(con):
    rows = con.execute("SELECT cert FROM analysis_low_capital_latest").fetchall()
    # Latest date in the data is 2011-06-30. Cert 1 has 4% equity then, so it is listed. Cert 2 is not in that quarter.
    assert rows == [(1,)]


def test_print_all_shows_each_query_title(con):
    import io
    from credit_risk.analysis import VIEWS, print_all

    out = io.StringIO()
    print_all(con, out=out)
    text = out.getvalue()
    for title, _ in VIEWS:
        assert title in text
    assert "(1 rows)" in text
