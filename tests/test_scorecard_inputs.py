from pathlib import Path

import duckdb
import pytest

ROOT = Path(__file__).resolve().parents[1]


def _view_connection():
    con = duckdb.connect(":memory:")
    for name in ("01_schema.sql", "03_ratios.sql", "04_scorecard_inputs.sql"):
        con.execute((ROOT / "sql" / name).read_text())
    con.execute("INSERT INTO bank_financials VALUES (1, '2020-12-31', 1000, 100, 600, 800, 12)")
    con.execute("INSERT INTO bank_capital_efficiency VALUES (1, '2020-12-31', 8.0, 6000, 50.0)")
    con.execute("INSERT INTO bank_financials VALUES (2, '2020-12-31', 500, 40, 300, 400, 3)")
    return con


def test_view_converts_percent_fields_to_fractions():
    row = _view_connection().execute(
        "SELECT tier1_leverage, efficiency_ratio FROM scorecard_inputs WHERE cert = 1"
    ).fetchone()
    assert row[0] == pytest.approx(0.08)
    assert row[1] == pytest.approx(0.50)


def test_allowance_to_loans_uses_gross_loans():
    value = _view_connection().execute(
        "SELECT allowance_to_loans FROM scorecard_inputs WHERE cert = 1"
    ).fetchone()[0]
    assert value == pytest.approx(6000 / (600 + 6000))


def test_missing_capital_row_gives_null_not_zero():
    row = _view_connection().execute(
        "SELECT tier1_leverage, allowance_to_loans, efficiency_ratio FROM scorecard_inputs WHERE cert = 2"
    ).fetchone()
    assert row == (None, None, None)
