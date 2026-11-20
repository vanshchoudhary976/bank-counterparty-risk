import duckdb
import pytest

from credit_risk.checks import DataChecks
from tests.sample_data import FAILURES, FINANCIALS, SOURCE_TOTALS


def _by_name(results, fragment):
    matches = [result for result in results if fragment in result.name]
    assert matches, f"no check name contains {fragment!r}"
    return matches[0]


def _failed(results):
    return [result for result in results if not result.passed]


def test_clean_synthetic_load_passes_every_check(loaded_warehouse):
    results = DataChecks(loaded_warehouse.con).run_all(SOURCE_TOTALS)
    assert _failed(results) == []


def test_row_count_mismatch_against_source_fails(loaded_warehouse):
    totals = dict(SOURCE_TOTALS, financials=len(FINANCIALS) + 10)
    results = DataChecks(loaded_warehouse.con).run_all(totals)
    result = _by_name(results, "stg_financials rows match API total")
    assert result.passed is False
    assert "stg_financials" in result.detail


def test_typed_row_loss_is_detected(loaded_warehouse):
    loaded_warehouse.con.execute("DELETE FROM bank_failures WHERE cert = 1004")
    results = DataChecks(loaded_warehouse.con).run_all(SOURCE_TOTALS)
    assert _by_name(results, "bank_failures rows match staged rows").passed is False


def test_duplicate_staged_keys_are_detected(warehouse):
    rows = [dict(FINANCIALS[0]), dict(FINANCIALS[0])]
    warehouse.load_staging("financials", rows, ["CERT", "REPDTE", "ASSET", "EQTOT", "LNLSNET", "DEP", "NETINC"])
    result = DataChecks(warehouse.con).no_duplicate_keys("stg_financials", ["CERT", "REPDTE"])
    assert result.passed is False


def test_off_quarter_end_date_is_detected(loaded_warehouse):
    loaded_warehouse.con.execute("UPDATE bank_financials SET report_date = DATE '2023-02-28' WHERE cert = 1002")
    result = DataChecks(loaded_warehouse.con).quarter_end_dates()
    assert result.passed is False


def test_null_amounts_above_tolerance_are_detected(loaded_warehouse):
    loaded_warehouse.con.execute("UPDATE bank_financials SET total_assets = NULL")
    result = DataChecks(loaded_warehouse.con).no_nulls(
        "bank_financials", ["total_assets", "total_equity"], max_share=0.01
    )
    assert result.passed is False


def test_null_keys_are_detected_in_staging_with_zero_tolerance(warehouse):
    # Staging accepts NULLs by design. Typed key columns are NOT NULL, so the check must run here.
    rows = [dict(FINANCIALS[0], CERT=None)]
    warehouse.load_staging("financials", rows, ["CERT", "REPDTE", "ASSET", "EQTOT", "LNLSNET", "DEP", "NETINC"])
    result = DataChecks(warehouse.con).no_nulls("stg_financials", ["CERT", "REPDTE"])
    assert result.passed is False


def test_typed_key_columns_reject_nulls(loaded_warehouse):
    with pytest.raises(duckdb.Error):
        loaded_warehouse.con.execute("UPDATE bank_financials SET cert = NULL WHERE cert = 1002")


def test_empty_table_fails_null_check(warehouse):
    result = DataChecks(warehouse.con).no_nulls("bank_financials", ["cert"])
    assert result.passed is False


def test_negative_assets_are_detected(loaded_warehouse):
    loaded_warehouse.con.execute("UPDATE bank_financials SET total_assets = -1 WHERE cert = 1002")
    assert DataChecks(loaded_warehouse.con).non_negative("bank_financials", "total_assets").passed is False


def test_equity_above_assets_is_detected(loaded_warehouse):
    loaded_warehouse.con.execute("UPDATE bank_financials SET total_equity = total_assets * 2 WHERE cert = 1002")
    assert DataChecks(loaded_warehouse.con).equity_not_above_assets().passed is False


def test_documented_equity_exception_is_excluded_but_reported(loaded_warehouse):
    # The real exception: cert 35137, 2005-09-30, equity 2,021 against assets 2,020 (thousands of USD).
    loaded_warehouse.con.execute(
        "INSERT INTO bank_financials VALUES (35137, DATE '2005-09-30', 2020.0, 2021.0, 1.0, 1.0, 1.0)"
    )
    result = DataChecks(loaded_warehouse.con).equity_not_above_assets()
    assert result.passed is True
    assert "0 unexplained" in result.detail
    assert "1 documented exception" in result.detail


def test_other_breach_still_fails_when_documented_exception_is_present(loaded_warehouse):
    loaded_warehouse.con.execute(
        "INSERT INTO bank_financials VALUES (35137, DATE '2005-09-30', 2020.0, 2021.0, 1.0, 1.0, 1.0)"
    )
    loaded_warehouse.con.execute("UPDATE bank_financials SET total_equity = total_assets * 2 WHERE cert = 1002")
    result = DataChecks(loaded_warehouse.con).equity_not_above_assets()
    assert result.passed is False
    assert "1 unexplained" in result.detail


def test_missing_known_2023_failure_is_detected(loaded_warehouse):
    loaded_warehouse.con.execute("DELETE FROM bank_failures WHERE cert = 1004")
    result = DataChecks(loaded_warehouse.con).known_2023_failures()
    assert result.passed is False
    assert "SIGNATURE" in result.detail


def test_known_failures_check_fails_when_table_is_empty(warehouse):
    assert DataChecks(warehouse.con).known_2023_failures().passed is False


def test_sec_check_fails_for_cik_without_facts(loaded_warehouse):
    result = DataChecks(loaded_warehouse.con).sec_facts_present([999])
    assert result.passed is False
    assert "999" in result.detail


def test_run_all_adds_sec_check_only_when_ciks_given(loaded_warehouse):
    checks = DataChecks(loaded_warehouse.con)
    assert all("SEC" not in result.name for result in checks.run_all(SOURCE_TOTALS))
    assert any("SEC" in result.name for result in checks.run_all(SOURCE_TOTALS, sec_ciks=[999]))


def test_failure_fixture_has_three_2023_events():
    assert len(FAILURES) == 3
