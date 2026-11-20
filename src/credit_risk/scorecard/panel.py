"""Load the modelling inputs from the warehouse.

Reads the bank_ratios view (Module A) and the first failure date per certificate number.
Failures with no certificate number (pre-insurance banks) cannot be matched and are left out,
which is recorded in docs/scorecard.md.
"""

from __future__ import annotations

from datetime import date
from typing import Mapping

RATIO_COLUMNS = ("equity_to_assets", "loans_to_deposits", "roa_annualised")


def load_panel(con) -> tuple[list[tuple[int, date, dict]], dict[int, date]]:
    """Return (rows, failures). rows are (cert, report_date, features) for every bank-quarter."""
    select_list = ", ".join(f"r.{c}" for c in RATIO_COLUMNS)
    rows = con.execute(
        f"SELECT r.cert, r.report_date, {select_list} FROM bank_ratios r ORDER BY r.cert, r.report_date"
    ).fetchall()
    panel = [
        (cert, report_date, dict(zip(RATIO_COLUMNS, values)))
        for cert, report_date, *values in rows
    ]
    failure_rows = con.execute(
        "SELECT cert, MIN(fail_date) FROM bank_failures WHERE cert IS NOT NULL GROUP BY cert"
    ).fetchall()
    failures: Mapping[int, date] = {cert: fail_date for cert, fail_date in failure_rows}
    return panel, dict(failures)
