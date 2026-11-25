from pathlib import Path

import duckdb
import pytest

from credit_risk.scorecard.panel import load_panel

SQL_DIR = Path(__file__).resolve().parents[1] / "sql"


@pytest.fixture()
def con():
    db = duckdb.connect(":memory:")
    for name in ("01_schema.sql", "03_ratios.sql", "04_scorecard_inputs.sql", "06_clean_inputs.sql"):
        db.execute((SQL_DIR / name).read_text(encoding="utf-8"))
    db.execute("INSERT INTO bank_financials VALUES (10, DATE '2010-12-31', 1000000, 100000, 600000, 800000, 5000)")
    db.execute("INSERT INTO bank_financials VALUES (11, DATE '2010-12-31', 2000, 2000, 0, 0, 5)")
    db.execute("INSERT INTO bank_capital_efficiency VALUES (10, DATE '2010-12-31', 9.0, 9000, 60.0)")
    db.execute("INSERT INTO bank_capital_efficiency VALUES (11, DATE '2010-12-31', 9.0, 0, 60.0)")
    yield db
    db.close()


def test_raw_view_keeps_every_bank(con):
    panel, _ = load_panel(con)
    assert {cert for cert, _, _ in panel} == {10, 11}


def test_clean_view_drops_the_empty_filer(con):
    panel, _ = load_panel(con, view="clean_scorecard_inputs")
    assert {cert for cert, _, _ in panel} == {10}


def test_unknown_view_is_refused(con):
    with pytest.raises(ValueError, match="view must be one of"):
        load_panel(con, view="bank_financials; DROP TABLE bank_financials")
