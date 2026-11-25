"""Read-only diagnostics on development and validation data (report dates 2005 to 2013).

This script never reads the test set (2014 onward) and never writes anything. It checks:
- the six scorecard inputs: count, missing values, and the spread from minimum to maximum,
- the most extreme values of each input, with cert and report date,
- the latest report date in the warehouse (to see whether post-2023 data exists for a fresh test window).

Run from the project folder:
    python scripts/diagnose_dev_val.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import duckdb

RATIOS = (
    "equity_to_assets",
    "tier1_leverage",
    "allowance_to_loans",
    "roa_annualised",
    "loans_to_deposits",
    "efficiency_ratio",
)
WINDOW = "report_date BETWEEN DATE '2005-01-01' AND DATE '2013-12-31'"


def default_database() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "warehouse.duckdb"


def summarise(con: duckdb.DuckDBPyConnection) -> None:
    print("Development and validation (2005 to 2013): spread of each input")
    print(f"  {'input':<20} {'count':>8} {'missing':>8} {'min':>12} {'1%':>12} {'median':>12} {'99%':>12} {'max':>12}")
    for r in RATIOS:
        n, missing, lo, p01, med, p99, hi = con.execute(
            f"""
            SELECT COUNT({r}), COUNT(*) - COUNT({r}), MIN({r}),
                   quantile_cont({r}, 0.01), quantile_cont({r}, 0.5),
                   quantile_cont({r}, 0.99), MAX({r})
            FROM scorecard_inputs WHERE {WINDOW}
            """
        ).fetchone()
        print(f"  {r:<20} {n:>8} {missing:>8} {lo:>12.5f} {p01:>12.5f} {med:>12.5f} {p99:>12.5f} {hi:>12.5f}")


def extremes(con: duckdb.DuckDBPyConnection, k: int = 5) -> None:
    for r in RATIOS:
        print(f"\nMost extreme values of {r} (2005 to 2013):")
        for label, order in (("highest", "DESC"), ("lowest", "ASC")):
            rows = con.execute(
                f"SELECT cert, report_date, {r} FROM scorecard_inputs "
                f"WHERE {WINDOW} AND {r} IS NOT NULL ORDER BY {r} {order} LIMIT {k}"
            ).fetchall()
            for cert, report_date, value in rows:
                print(f"  {label:<8} cert {cert}, {report_date}, value {value:.5f}")


def latest_date(con: duckdb.DuckDBPyConnection) -> None:
    (latest,) = con.execute("SELECT MAX(report_date) FROM scorecard_inputs").fetchone()
    print(f"\nLatest report date in the warehouse: {latest}")


def main(argv: list[str]) -> int:
    path = Path(argv[1]) if len(argv) > 1 else default_database()
    if not path.exists():
        print(f"Warehouse not found at {path}. Run make load first.")
        return 1
    con = duckdb.connect(str(path), read_only=True)
    try:
        summarise(con)
        extremes(con)
        latest_date(con)
    finally:
        con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
