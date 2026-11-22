"""Read-only raw-field check on development and validation data (report dates 2005 to 2013).

Never reads the test set (2014 onward) and never writes anything. It answers three questions:

1. Units: is the FDIC percentage field (Tier 1 leverage, efficiency ratio) the same scale in every year?
   A jump between years would mean some years are fractions and others percentages.
2. Denominators: how many rows have a zero, negative or missing denominator, which makes a ratio meaningless?
3. Extremes: for the most extreme ratio values, what are the raw inputs behind them?

Run from the project folder:
    python scripts/raw_check_dev_val.py
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
WINDOW = "f.report_date BETWEEN DATE '2005-01-01' AND DATE '2013-12-31'"


def default_database() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "warehouse.duckdb"


def units_by_year(con: duckdb.DuckDBPyConnection) -> None:
    print("1. Units by year: raw FDIC percentage fields (should be percentages, e.g. about 9 to 10 for Tier 1)")
    print(f"  {'year':>4}  {'T1 median':>10} {'T1 max':>10} {'T1 > 100':>9}   {'eff median':>10} {'eff max':>10} {'eff > 100':>10}")
    rows = con.execute(
        f"""
        SELECT EXTRACT(YEAR FROM f.report_date) AS yr,
               quantile_cont(c.tier1_leverage_pct, 0.5), MAX(c.tier1_leverage_pct),
               SUM(CASE WHEN c.tier1_leverage_pct > 100 THEN 1 ELSE 0 END),
               quantile_cont(c.efficiency_ratio_pct, 0.5), MAX(c.efficiency_ratio_pct),
               SUM(CASE WHEN c.efficiency_ratio_pct > 100 THEN 1 ELSE 0 END)
        FROM bank_financials AS f
        LEFT JOIN bank_capital_efficiency AS c ON c.cert = f.cert AND c.report_date = f.report_date
        WHERE {WINDOW}
        GROUP BY yr ORDER BY yr
        """
    ).fetchall()
    for yr, t1_med, t1_max, t1_over, eff_med, eff_max, eff_over in rows:
        print(f"  {int(yr):>4}  {fmt(t1_med):>10} {fmt(t1_max):>10} {int(t1_over or 0):>9}   "
              f"{fmt(eff_med):>10} {fmt(eff_max):>10} {int(eff_over or 0):>10}")


def denominators(con: duckdb.DuckDBPyConnection) -> None:
    print("\n2. Denominators (dev and validation): rows where a ratio cannot be defined or is impossible")
    checks = {
        "total assets <= 0 or missing": "f.total_assets IS NULL OR f.total_assets <= 0",
        "total equity < 0 (negative equity)": "f.total_equity < 0",
        "deposits <= 0 or missing": "f.total_deposits IS NULL OR f.total_deposits <= 0",
        "gross loans <= 0 or missing": "(f.net_loans + COALESCE(c.allowance_for_loans, 0)) IS NULL "
                                       "OR (f.net_loans + COALESCE(c.allowance_for_loans, 0)) <= 0",
        "net loans <= 0 (allowance ratio becomes 1.0)": "f.net_loans IS NULL OR f.net_loans <= 0",
        "Tier 1 field missing": "c.tier1_leverage_pct IS NULL",
        "efficiency field missing": "c.efficiency_ratio_pct IS NULL",
    }
    total = con.execute(
        f"SELECT COUNT(*) FROM bank_financials AS f WHERE {WINDOW}"
    ).fetchone()[0]
    print(f"  bank-quarters in window: {total}")
    for label, condition in checks.items():
        (count,) = con.execute(
            f"""
            SELECT COUNT(*) FROM bank_financials AS f
            LEFT JOIN bank_capital_efficiency AS c ON c.cert = f.cert AND c.report_date = f.report_date
            WHERE {WINDOW} AND ({condition})
            """
        ).fetchone()
        print(f"  {label:<36} {count:>8}")


def extremes(con: duckdb.DuckDBPyConnection, k: int = 3) -> None:
    print("\n3. Raw inputs behind the extreme ratio values (dev and validation)")
    for r in RATIOS:
        for label, order in (("highest", "DESC"), ("lowest", "ASC")):
            rows = con.execute(
                f"""
                SELECT s.cert, s.report_date, s.{r},
                       f.total_assets, f.total_equity, f.net_loans, f.total_deposits, f.net_income,
                       c.tier1_leverage_pct, c.allowance_for_loans, c.efficiency_ratio_pct
                FROM scorecard_inputs AS s
                JOIN bank_financials AS f ON f.cert = s.cert AND f.report_date = s.report_date
                LEFT JOIN bank_capital_efficiency AS c ON c.cert = s.cert AND c.report_date = s.report_date
                WHERE f.report_date BETWEEN DATE '2005-01-01' AND DATE '2013-12-31'
                  AND s.{r} IS NOT NULL
                ORDER BY s.{r} {order} LIMIT {k}
                """
            ).fetchall()
            for row in rows:
                cert, report_date, value, assets, equity, loans, deposits, income, t1, allow, eff = row
                print(f"  {r} {label}: cert {cert}, {report_date}, ratio {fmt(value)}")
                print(f"      assets {fmt(assets)}, equity {fmt(equity)}, net loans {fmt(loans)}, "
                      f"deposits {fmt(deposits)}, net income {fmt(income)}")
                print(f"      raw Tier 1 pct {fmt(t1)}, allowance {fmt(allow)}, raw efficiency pct {fmt(eff)}")


def fmt(value) -> str:
    if value is None:
        return "NULL"
    return f"{value:,.4f}" if abs(value) < 1000 else f"{value:,.0f}"


def main(argv: list[str]) -> int:
    path = Path(argv[1]) if len(argv) > 1 else default_database()
    if not path.exists():
        print(f"Warehouse not found at {path}. Run make load first.")
        return 1
    con = duckdb.connect(str(path), read_only=True)
    try:
        units_by_year(con)
        denominators(con)
        extremes(con)
    finally:
        con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
