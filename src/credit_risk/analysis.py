"""Week 2 analysis: print the five peer-group queries from sql/05_analysis.sql.

Run with: python -m credit_risk.analysis
The views are created by the load step (make load), so run that first.
"""

from __future__ import annotations

from typing import TextIO
import sys

import duckdb

from credit_risk.config import ProjectPaths

VIEWS: tuple[tuple[str, str], ...] = (
    ("Query 1: median equity to assets by size band and year", "analysis_equity_to_assets_by_band"),
    ("Query 2: median annualised ROA by size band and year", "analysis_roa_by_band_year"),
    ("Query 3: share of banks with loans above deposits, by size band and year", "analysis_loans_above_deposits_by_band"),
    ("Query 4: failures by year and size band (band of last report before failure)", "analysis_failures_by_band_year"),
    ("Query 5: banks with equity to assets below 5% in the latest quarter", "analysis_low_capital_latest"),
)


def print_all(con: duckdb.DuckDBPyConnection, out: TextIO = sys.stdout) -> None:
    for title, view in VIEWS:
        cursor = con.execute(f"SELECT * FROM {view}")
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        print(f"\n{title}", file=out)
        print(" | ".join(columns), file=out)
        for row in rows:
            print(" | ".join(_format(value) for value in row), file=out)
        print(f"({len(rows)} rows)", file=out)


def _format(value: object) -> str:
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def main() -> int:
    con = duckdb.connect(str(ProjectPaths.default().warehouse_file), read_only=True)
    try:
        print_all(con)
    finally:
        con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
