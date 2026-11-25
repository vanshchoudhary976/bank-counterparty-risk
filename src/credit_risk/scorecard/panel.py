"""Load the modelling inputs from the warehouse.

Reads the bank_ratios view (Module A) and the first failure date per certificate number.
Failures with no certificate number (pre-insurance banks) cannot be matched and are left out,
which is recorded in docs/scorecard.md.
"""

from __future__ import annotations

from datetime import date
from typing import Mapping

RATIO_COLUMNS = (
    "equity_to_assets",
    "tier1_leverage",
    "allowance_to_loans",
    "roa_annualised",
    "efficiency_ratio",
    "loans_to_deposits",
)


# Only these views may be read. The name goes into SQL text, so it must come from this list.
ALLOWED_VIEWS = ("scorecard_inputs", "clean_scorecard_inputs")


def load_panel(con, view: str = "scorecard_inputs") -> tuple[list[tuple[int, date, dict]], dict[int, date]]:
    """Return (rows, failures). rows are (cert, report_date, features) for every bank-quarter in the view.

    Week 3 reads the raw scorecard_inputs view. Week 4 reads clean_scorecard_inputs, where the drop rules
    and the zero-efficiency rule are applied (docs/ratio_definitions.md).
    """
    if view not in ALLOWED_VIEWS:
        raise ValueError(f"view must be one of {ALLOWED_VIEWS}, got {view!r}")
    select_list = ", ".join(f"s.{c}" for c in RATIO_COLUMNS)
    rows = con.execute(
        f"SELECT s.cert, s.report_date, {select_list} FROM {view} s ORDER BY s.cert, s.report_date"
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
