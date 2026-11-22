import pytest
from datetime import date
from pathlib import Path

import duckdb

from credit_risk.scorecard.panel import load_panel

ROOT = Path(__file__).resolve().parents[1]


def _connection():
    con = duckdb.connect(":memory:")
    con.execute((ROOT / "sql" / "01_schema.sql").read_text())
    con.execute((ROOT / "sql" / "03_ratios.sql").read_text())
    con.execute((ROOT / "sql" / "04_scorecard_inputs.sql").read_text())
    con.execute(
        """
        INSERT INTO bank_financials VALUES
          (1, '2020-03-31', 1000, 100, 600, 800, 10),
          (1, '2020-06-30', 1000, 100, 600, 800, 20),
          (2, '2020-03-31', 2000, 300, 900, 1000, 30)
        """
    )
    con.execute(
        """
        INSERT INTO bank_capital_efficiency VALUES
          (1, '2020-03-31', 9.5, 6, 60.0),
          (1, '2020-06-30', 9.5, 6, 60.0),
          (2, '2020-03-31', 8.0, 9, 55.0)
        """
    )
    con.execute(
        """
        INSERT INTO bank_failures VALUES
          (1, 'Bank One', '2021-05-01'),
          (1, 'Bank One', '2022-01-01'),
          (NULL, 'Pre-insurance bank', '1930-01-01')
        """
    )
    return con


def test_load_panel_returns_ratio_features_for_each_bank_quarter():
    rows, _ = load_panel(_connection())
    assert [(cert, report_date) for cert, report_date, _ in rows] == [
        (1, date(2020, 3, 31)),
        (1, date(2020, 6, 30)),
        (2, date(2020, 3, 31)),
    ]
    first = rows[0][2]
    assert set(first) == {
        "equity_to_assets", "tier1_leverage", "allowance_to_loans",
        "roa_annualised", "efficiency_ratio", "loans_to_deposits",
    }
    assert first["equity_to_assets"] == 0.1
    assert first["loans_to_deposits"] == 0.75
    assert first["tier1_leverage"] == pytest.approx(0.095)
    assert first["allowance_to_loans"] == pytest.approx(6000 / 606000)
    assert first["efficiency_ratio"] == pytest.approx(0.60)


def test_load_panel_takes_first_failure_date_and_skips_missing_cert():
    _, failures = load_panel(_connection())
    assert failures == {1: date(2021, 5, 1)}
