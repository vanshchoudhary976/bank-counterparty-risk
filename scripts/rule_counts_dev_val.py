"""Read-only counts for the cleaning rules, on development and validation data only (2005 to 2013).

Never reads the test set (2014 onward) and never writes anything.

Rules (decided 22 November 2026):
- Rule 1: zero deposits and zero net loans. Dropped (non-operating or non-lending filer).
- Rule 2: equity above total assets. Dropped (reporting error).
- Rule 3: negative equity on a normal balance sheet. Kept. Counted for information only.
- Rule 4: exact efficiency ratio of 0. Treated as missing, not dropped.
- Rule 5: cap each input at the 1st and 99th percentiles of development data, after rules 1 to 6,
  and apply the same caps to validation.
- Rule 6: implausible capital. Dropped if Tier 1 leverage is above 50% or equity is above half of total assets.
  No deposit-taking bank holds that much capital, so these values are reporting errors. Added 22 November 2026
  after the rule 5 check showed the 99th percentile itself was set by such rows.

Run from the project folder:
    python scripts/rule_counts_dev_val.py
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
DEV_VAL = "f.report_date BETWEEN DATE '2005-01-01' AND DATE '2013-12-31'"
DEV = "f.report_date BETWEEN DATE '2005-01-01' AND DATE '2010-12-31'"
VAL = "f.report_date BETWEEN DATE '2011-01-01' AND DATE '2013-12-31'"

RULE_1 = "COALESCE(f.total_deposits, 0) = 0 AND COALESCE(f.net_loans, 0) = 0"
RULE_2 = "f.total_equity > f.total_assets"
RULE_3 = "f.total_equity < 0"
RULE_4 = "c.efficiency_ratio_pct = 0"
RULE_6 = "c.tier1_leverage_pct > 50 OR f.total_equity > 0.5 * f.total_assets"
DROPPED = f"COALESCE(({RULE_1}) OR ({RULE_2}) OR ({RULE_6}), FALSE)"
KEEP = f"NOT ({DROPPED})"
FROM_JOIN = (
    "FROM bank_financials AS f "
    "LEFT JOIN bank_capital_efficiency AS c ON c.cert = f.cert AND c.report_date = f.report_date"
)


def default_database() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "warehouse.duckdb"


def count(con, condition: str) -> int:
    (n,) = con.execute(f"SELECT COUNT(*) {FROM_JOIN} WHERE {condition}").fetchone()
    return n


def rule_counts(con) -> None:
    print("Rule counts, development and validation (2005 to 2013)")
    print(f"  bank-quarters in window:                 {count(con, DEV_VAL):>8}")
    for label, rule in (
        ("Rule 1 zero deposits and zero loans", RULE_1),
        ("Rule 2 equity above assets", RULE_2),
        ("Rule 3 negative equity (kept)", RULE_3),
        ("Rule 4 efficiency exactly 0 (set missing)", RULE_4),
        ("Rule 6 implausible capital", RULE_6),
    ):
        print(f"  {label:<42} {count(con, f'({DEV_VAL}) AND COALESCE(({rule}), FALSE)'):>8}")
    print(f"  dropped by rules 1, 2 or 6 (union)       {count(con, f'({DEV_VAL}) AND {DROPPED}'):>8}")
    print(f"  kept after rules 1, 2 and 6              {count(con, f'({DEV_VAL}) AND {KEEP}'):>8}")


def cap_counts(con) -> None:
    print("\nRule 5 caps (after rules 1, 2 and 6): development 1st and 99th percentiles, rows outside them in validation")
    print(f"  {'input':<20} {'low cap':>12} {'high cap':>12} {'val below':>10} {'val above':>10} {'val total':>10}")
    for r in RATIOS:
        value = f"CASE WHEN c.efficiency_ratio_pct = 0 THEN NULL ELSE s.{r} END" if r == "efficiency_ratio" else f"s.{r}"
        base = (
            f"FROM scorecard_inputs AS s "
            f"JOIN bank_financials AS f ON f.cert = s.cert AND f.report_date = s.report_date "
            f"LEFT JOIN bank_capital_efficiency AS c ON c.cert = s.cert AND c.report_date = s.report_date "
            f"WHERE {KEEP} AND "
        )
        lo, hi = con.execute(
            f"SELECT quantile_cont({value}, 0.01), quantile_cont({value}, 0.99) {base}{DEV} AND ({value}) IS NOT NULL"
        ).fetchone()
        below, above, total = con.execute(
            f"SELECT SUM(CASE WHEN ({value}) < {lo} THEN 1 ELSE 0 END), "
            f"SUM(CASE WHEN ({value}) > {hi} THEN 1 ELSE 0 END), COUNT({value}) "
            f"{base}{VAL}"
        ).fetchone()
        print(f"  {r:<20} {lo:>12.5f} {hi:>12.5f} {int(below or 0):>10} {int(above or 0):>10} {int(total or 0):>10}")


def main(argv: list[str]) -> int:
    path = Path(argv[1]) if len(argv) > 1 else default_database()
    if not path.exists():
        print(f"Warehouse not found at {path}. Run make load first.")
        return 1
    con = duckdb.connect(str(path), read_only=True)
    try:
        rule_counts(con)
        cap_counts(con)
    finally:
        con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
