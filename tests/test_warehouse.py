from datetime import date

import duckdb
import pytest

from credit_risk.warehouse import Warehouse, validate_identifier
from tests.conftest import SQL_DIR
from tests.sample_data import FAILURES, FINANCIALS, INSTITUTIONS


def test_schema_creates_expected_tables(warehouse):
    names = {row[0] for row in warehouse.con.execute("SELECT table_name FROM information_schema.tables").fetchall()}
    assert {"institutions", "bank_financials", "bank_failures", "sec_facts", "load_log"} <= names


def test_schema_is_safe_to_rerun(warehouse):
    warehouse.apply_sql_file(SQL_DIR / "01_schema.sql")
    assert warehouse.count("bank_financials") == 0


def test_staging_stores_text_and_keeps_nulls(warehouse):
    count = warehouse.load_staging("demo", [{"A": "1", "B": None}, {"A": "2", "B": "x"}], ["A", "B"])
    assert count == 2
    rows = warehouse.con.execute("SELECT A, B FROM stg_demo ORDER BY A").fetchall()
    assert rows == [("1", None), ("2", "x")]


def test_staging_converts_numbers_to_text(warehouse):
    warehouse.load_staging("demo", [{"A": 1001}], ["A"])
    assert warehouse.con.execute("SELECT A FROM stg_demo").fetchone()[0] == "1001"


def test_staging_rejects_unsafe_column_names(warehouse):
    with pytest.raises(ValueError):
        warehouse.load_staging("demo", [], ["A; DROP TABLE institutions"])


def test_validate_identifier_accepts_plain_names_only():
    assert validate_identifier("REPDTE") == "REPDTE"
    with pytest.raises(ValueError):
        validate_identifier("1bad")
    with pytest.raises(ValueError):
        validate_identifier("a b")


def test_typed_build_casts_values(loaded_warehouse):
    row = loaded_warehouse.con.execute(
        "SELECT report_date, total_assets, total_equity FROM bank_financials "
        "WHERE cert = 1001 ORDER BY report_date LIMIT 1"
    ).fetchone()
    assert row[0] == date(2023, 3, 31)
    assert row[1] == 1000000.0
    assert row[2] == 90000.0


def test_typed_row_counts_match_staging(loaded_warehouse):
    assert loaded_warehouse.count("institutions") == len(INSTITUTIONS)
    assert loaded_warehouse.count("bank_financials") == len(FINANCIALS)
    assert loaded_warehouse.count("bank_failures") == len(FAILURES)


def test_failure_dates_are_typed(loaded_warehouse):
    years = loaded_warehouse.con.execute("SELECT DISTINCT year(fail_date) FROM bank_failures").fetchall()
    assert years == [(2023,)]


def test_failure_dates_accept_fdic_slash_format(warehouse):
    warehouse.load_staging("institutions", INSTITUTIONS, ["CERT", "NAME", "STALP", "ACTIVE"])
    warehouse.load_staging(
        "financials",
        [{"CERT": "1001", "REPDTE": "20231231", "ASSET": "1", "EQTOT": "1", "LNLSNET": "1", "DEP": "1", "NETINC": "1",
          "RBC1AAJ": "1", "LNLSRES": "1", "EEFFR": "1"}],
        ["CERT", "REPDTE", "ASSET", "EQTOT", "LNLSNET", "DEP", "NETINC", "RBC1AAJ", "LNLSRES", "EEFFR"],
    )
    warehouse.load_staging(
        "failures",
        [{"CERT": None, "NAME": "FON DU LAC STATE BANK", "FAILDATE": "5/28/1934"},
         {"CERT": "1004", "NAME": "SIGNATURE BANK", "FAILDATE": "1/3/2023"}],
        ["CERT", "NAME", "FAILDATE"],
    )
    warehouse.build_typed_tables(SQL_DIR / "02_load_fdic.sql")
    rows = warehouse.con.execute("SELECT cert, fail_date FROM bank_failures ORDER BY fail_date").fetchall()
    assert rows == [(None, date(1934, 5, 28)), (1004, date(2023, 1, 3))]


def test_typed_build_is_repeatable(loaded_warehouse):
    before = loaded_warehouse.count("bank_financials")
    loaded_warehouse.build_typed_tables(SQL_DIR / "02_load_fdic.sql")
    assert loaded_warehouse.count("bank_financials") == before


def test_unparseable_report_date_fails_loudly(warehouse):
    warehouse.load_staging("institutions", INSTITUTIONS, ["CERT", "NAME", "STALP", "ACTIVE"])
    warehouse.load_staging(
        "financials",
        [{"CERT": "1001", "REPDTE": "2023-12-31", "ASSET": "1", "EQTOT": "1", "LNLSNET": "1", "DEP": "1", "NETINC": "1",
          "RBC1AAJ": "1", "LNLSRES": "1", "EEFFR": "1"}],
        ["CERT", "REPDTE", "ASSET", "EQTOT", "LNLSNET", "DEP", "NETINC", "RBC1AAJ", "LNLSRES", "EEFFR"],
    )
    warehouse.load_staging("failures", FAILURES, ["CERT", "NAME", "FAILDATE"])
    with pytest.raises(duckdb.Error):
        warehouse.build_typed_tables(SQL_DIR / "02_load_fdic.sql")


def test_record_load_writes_traceable_log_row(warehouse):
    warehouse.record_load("stg_financials", "fdic_financials_20261119T120000Z.json", "abc123", 6, 6)
    row = warehouse.con.execute("SELECT table_name, source_sha256, rows_staged FROM load_log").fetchone()
    assert row == ("stg_financials", "abc123", 6)


def test_sec_facts_are_replaced_per_company(warehouse):
    first = [
        {"taxonomy": "us-gaap", "concept": "Revenues", "unit": "USD", "period_end": "2022-12-31", "val": 1.0,
         "fiscal_year": 2022, "fiscal_period": "FY", "form": "10-K", "filed": "2023-02-01", "accession": "a"},
        {"taxonomy": "us-gaap", "concept": "Revenues", "unit": "USD", "period_end": "2023-12-31", "val": 2.0,
         "fiscal_year": 2023, "fiscal_period": "FY", "form": "10-K", "filed": "2024-02-01", "accession": "b"},
    ]
    warehouse.load_sec_facts(320193, first)
    assert warehouse.count("sec_facts") == 2
    warehouse.load_sec_facts(320193, first[:1])
    assert warehouse.count("sec_facts") == 1


def test_sec_facts_reload_keeps_other_companies(warehouse):
    row = {"taxonomy": "dei", "concept": "EntityName", "unit": "pure", "period_end": "2023-12-31", "val": 0.0,
           "fiscal_year": 2023, "fiscal_period": "FY", "form": "10-K", "filed": "2024-01-01", "accession": "c"}
    warehouse.load_sec_facts(1, [row])
    warehouse.load_sec_facts(2, [row])
    warehouse.load_sec_facts(1, [])
    assert warehouse.con.execute("SELECT COUNT(*) FROM sec_facts WHERE cik = 2").fetchone()[0] == 1


def test_warehouse_file_is_created_under_parent_folder(tmp_path):
    target = tmp_path / "nested" / "warehouse.duckdb"
    wh = Warehouse(target)
    wh.close()
    assert target.exists()
