"""Data checks run after each load.

A check never changes data. It returns a CheckResult, and the loader exits with
status 1 if any result failed. Each check states what it proves so it can be defended in an interview.
"""

from __future__ import annotations

from dataclasses import dataclass

import duckdb

from credit_risk.warehouse import validate_identifier

# Name fragments of the three 2023 failures in the synthetic test fixture and in real data.
KNOWN_2023_FAILURES: tuple[str, ...] = ("SILICON VALLEY", "SIGNATURE", "FIRST REPUBLIC")

# Documented exceptions to "equity does not exceed total assets". Each one was reviewed by hand.
# Cert 35137, report date 2005-09-30: total assets 2,020 and equity 2,021 (thousands of USD),
# a $1,000 breach at a very small bank, most likely rounding in the source data.
# The row stays in the warehouse. Any other breach still fails the load.
KNOWN_EQUITY_EXCEPTIONS: tuple[tuple[int, str], ...] = ((35137, "2005-09-30"),)


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    detail: str


class DataChecks:
    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self.con = con

    def _scalar(self, sql: str, params: list | None = None):
        return self.con.execute(sql, params or []).fetchone()[0]

    def _count(self, table: str) -> int:
        return self._scalar(f"SELECT COUNT(*) FROM {validate_identifier(table)}")

    def row_count_matches(self, table: str, expected: int, label: str) -> CheckResult:
        """Proves that nothing was lost between the API, staging and the typed tables."""
        actual = self._count(table)
        return CheckResult(
            f"{table} rows match {label}",
            actual == expected,
            f"{table}={actual}, {label}={expected}",
        )

    def no_duplicate_keys(self, table: str, keys: list[str]) -> CheckResult:
        key_sql = ", ".join(validate_identifier(key) for key in keys)
        table_sql = validate_identifier(table)
        duplicated = self._scalar(
            f"SELECT COUNT(*) FROM (SELECT {key_sql} FROM {table_sql} GROUP BY {key_sql} HAVING COUNT(*) > 1)"
        )
        return CheckResult(
            f"no duplicate keys in {table} ({key_sql})",
            duplicated == 0,
            f"{duplicated} duplicated key(s)",
        )

    def no_nulls(self, table: str, columns: list[str], max_share: float = 0.0) -> CheckResult:
        """Share of rows with a NULL in any listed column must not exceed max_share."""
        table_sql = validate_identifier(table)
        cols = [validate_identifier(column) for column in columns]
        total = self._count(table)
        if total == 0:
            return CheckResult(f"nulls in {table}", False, "table is empty")
        where = " OR ".join(f"{column} IS NULL" for column in cols)
        nulls = self._scalar(f"SELECT COUNT(*) FROM {table_sql} WHERE {where}")
        share = nulls / total
        return CheckResult(
            f"rows with a null in {', '.join(cols)} at most {max_share:.1%}",
            share <= max_share,
            f"{nulls} of {total} rows ({share:.2%})",
        )

    def quarter_end_dates(self, table: str = "bank_financials", column: str = "report_date") -> CheckResult:
        """Call Report data is dated at quarter ends. Any other date means a parsing error."""
        table_sql = validate_identifier(table)
        column_sql = validate_identifier(column)
        bad = self._scalar(
            f"SELECT COUNT(*) FROM {table_sql} "
            f"WHERE NOT (month({column_sql}) IN (3, 6, 9, 12) AND {column_sql} = last_day({column_sql}))"
        )
        return CheckResult(f"{column} falls on a quarter end", bad == 0, f"{bad} row(s) off quarter end")

    def non_negative(self, table: str, column: str) -> CheckResult:
        table_sql = validate_identifier(table)
        column_sql = validate_identifier(column)
        bad = self._scalar(f"SELECT COUNT(*) FROM {table_sql} WHERE {column_sql} < 0")
        return CheckResult(f"{column} is not negative", bad == 0, f"{bad} negative value(s)")

    def equity_not_above_assets(self) -> CheckResult:
        """Equity cannot exceed total assets on a balance sheet, so this catches swapped or mis-scaled fields.
        Breaches listed in KNOWN_EQUITY_EXCEPTIONS are counted and reported, but do not fail the check."""
        breaches = self._scalar("SELECT COUNT(*) FROM bank_financials WHERE total_equity > total_assets")
        if KNOWN_EQUITY_EXCEPTIONS:
            match = " OR ".join("(cert = ? AND report_date = CAST(? AS DATE))" for _ in KNOWN_EQUITY_EXCEPTIONS)
            params = [value for pair in KNOWN_EQUITY_EXCEPTIONS for value in pair]
            excepted = self._scalar(
                f"SELECT COUNT(*) FROM bank_financials WHERE total_equity > total_assets AND ({match})", params
            )
        else:
            excepted = 0
        unexplained = breaches - excepted
        return CheckResult(
            "total equity does not exceed total assets",
            unexplained == 0,
            f"{unexplained} unexplained breach(es); {excepted} documented exception(s) excluded",
        )

    def known_2023_failures(self) -> CheckResult:
        names = [
            str(row[0]).upper()
            for row in self.con.execute(
                "SELECT bank_name FROM bank_failures WHERE year(fail_date) = 2023"
            ).fetchall()
            if row[0] is not None
        ]
        missing = [fragment for fragment in KNOWN_2023_FAILURES if not any(fragment in name for name in names)]
        return CheckResult(
            "known 2023 failures present in bank_failures",
            not missing,
            f"missing: {', '.join(missing) if missing else 'none'}",
        )

    def failures_without_cert(self) -> CheckResult:
        """Information only. Early failures (before deposit insurance) legitimately have no certificate number."""
        missing = self._scalar("SELECT COUNT(*) FROM bank_failures WHERE cert IS NULL")
        total = self._count("bank_failures")
        earliest = self._scalar("SELECT MIN(fail_date) FROM bank_failures")
        return CheckResult(
            "failures with no CERT (information only)",
            True,
            f"{missing} of {total} failures have no CERT; earliest failure date {earliest}",
        )

    def sec_facts_present(self, ciks: list[int]) -> CheckResult:
        empty = [cik for cik in ciks if self._scalar("SELECT COUNT(*) FROM sec_facts WHERE cik = ?", [cik]) == 0]
        return CheckResult(
            "SEC facts loaded for every CIK",
            not empty,
            f"CIKs with no facts: {empty if empty else 'none'}",
        )

    def run_all(self, source_totals: dict[str, int], sec_ciks: list[int] | None = None) -> list[CheckResult]:
        staged_financials = self._count("stg_financials")
        staged_failures = self._count("stg_failures")
        staged_institutions = self._count("stg_institutions")
        results = [
            self.row_count_matches("stg_financials", source_totals["financials"], "API total"),
            self.row_count_matches("stg_institutions", source_totals["institutions"], "API total"),
            self.row_count_matches("stg_failures", source_totals["failures"], "API total"),
            self.row_count_matches("bank_financials", staged_financials, "staged rows"),
            self.row_count_matches("bank_failures", staged_failures, "staged rows"),
            self.row_count_matches("institutions", staged_institutions, "staged rows"),
            self.no_duplicate_keys("stg_financials", ["CERT", "REPDTE"]),
            # Keys are checked in staging because the typed key columns are NOT NULL and would reject a null outright.
            self.no_nulls("stg_financials", ["CERT", "REPDTE"]),
            self.no_nulls("bank_financials", ["total_assets", "total_equity"], max_share=0.01),
            self.quarter_end_dates(),
            self.non_negative("bank_financials", "total_assets"),
            self.equity_not_above_assets(),
            self.known_2023_failures(),
            self.failures_without_cert(),
        ]
        if sec_ciks:
            results.append(self.sec_facts_present(sec_ciks))
        return results
