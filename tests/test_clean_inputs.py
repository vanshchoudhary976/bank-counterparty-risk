from pathlib import Path

import duckdb
import pytest

SQL_DIR = Path(__file__).resolve().parents[1] / "sql"
D = "DATE '2010-12-31'"


@pytest.fixture()
def con():
    db = duckdb.connect(":memory:")
    for name in ("01_schema.sql", "03_ratios.sql", "04_scorecard_inputs.sql", "06_clean_inputs.sql"):
        db.execute((SQL_DIR / name).read_text(encoding="utf-8"))
    # (cert, assets, equity, net loans, deposits, tier1 pct, efficiency pct)
    rows = [
        (10, 1_000_000, 100_000, 600_000, 800_000, 9.0, 60.0),   # normal: kept
        (11, 2_000, 2_000, 0, 0, 9.0, 60.0),                      # rule 1 and 2: dropped
        (12, 1_000, 1_100, 500, 800, 9.0, 60.0),                  # rule 2 only: dropped
        (13, 1_000_000, -50_000, 600_000, 800_000, 9.0, 60.0),    # negative equity, normal: kept
        (14, 1_000_000, 100_000, 600_000, 800_000, 60.0, 60.0),   # rule 6 via Tier 1: dropped
        (15, 1_000_000, 600_000, 300_000, 800_000, 9.0, 60.0),    # rule 6 via equity share: dropped
        (16, 1_000_000, 100_000, 600_000, 800_000, 9.0, 0.0),     # rule 4: kept, efficiency NULL
    ]
    for cert, assets, equity, loans, deposits, t1, eff in rows:
        db.execute(
            "INSERT INTO bank_financials VALUES (?, DATE '2010-12-31', ?, ?, ?, ?, 5000)",
            [cert, assets, equity, loans, deposits],
        )
        db.execute(
            "INSERT INTO bank_capital_efficiency VALUES (?, DATE '2010-12-31', ?, 9000, ?)",
            [cert, t1, eff],
        )
    yield db
    db.close()


def _kept(con):
    return {cert: eff for cert, eff in con.execute(
        "SELECT cert, efficiency_ratio FROM clean_scorecard_inputs"
    ).fetchall()}


def test_rules_drop_the_right_banks(con):
    assert set(_kept(con)) == {10, 13, 16}


def test_negative_equity_is_kept_with_its_real_ratio(con):
    (ratio,) = con.execute(
        "SELECT equity_to_assets FROM clean_scorecard_inputs WHERE cert = 13"
    ).fetchone()
    assert ratio == pytest.approx(-0.05)


def test_zero_efficiency_becomes_missing(con):
    kept = _kept(con)
    assert kept[16] is None
    assert kept[10] == pytest.approx(0.6)


def test_clean_view_keeps_every_other_input_unchanged(con):
    (roa,) = con.execute(
        "SELECT roa_annualised FROM clean_scorecard_inputs WHERE cert = 10"
    ).fetchone()
    (raw,) = con.execute("SELECT roa_annualised FROM scorecard_inputs WHERE cert = 10").fetchone()
    assert roa == pytest.approx(raw)
