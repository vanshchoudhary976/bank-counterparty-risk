"""Diagnose the early-warning back-test: which rule fires on survivors and on failures, quarter by quarter.

Read-only. It does not change any threshold. It explains the back-test result in run_warning.
"""

from __future__ import annotations

from collections import Counter
from datetime import date
from pathlib import Path
from typing import Mapping, Sequence

from credit_risk.warning.rules import PeerThresholds, Row, evaluate

RULE_NAMES = (
    "tier1 below floor",
    "tier1 below peer 25th percentile",
    "loans to deposits above 100% and rising four quarters",
    "loans to deposits above peer 75th percentile",
    "rating downgrade of two notches or grade 8 and worse",
    "rating downgrade of one notch",
    "asset growth above 40% with falling capital",
    "asset growth above 25% a year",
)


def diagnose(
    rows_by_cert: Mapping[int, Sequence[Row]],
    failures: Mapping[int, date],
    start: date,
    end: date,
    peers_by_quarter: Mapping[date, PeerThresholds],
) -> dict:
    survivor_quarters = 0
    survivor_quarters_red = 0
    rule_red_survivor = Counter()
    rule_red_failure_quarters = Counter()
    failure_quarters = 0
    for cert, rows in rows_by_cert.items():
        rows = sorted((r for r in rows if start <= r.report_date <= end), key=lambda x: x.report_date)
        fail_date = failures.get(cert)
        history: list[Row] = []
        for r in rows:
            if fail_date is not None and r.report_date >= fail_date:
                break
            history.append(r)
            fired = evaluate(history, peers_by_quarter[r.report_date])
            reds = {rule for rule, c in fired if c == "red"}
            if fail_date is not None and fail_date <= end:
                failure_quarters += 1
                rule_red_failure_quarters.update(reds)
            elif fail_date is None or fail_date > end:
                survivor_quarters += 1
                if reds:
                    survivor_quarters_red += 1
                rule_red_survivor.update(reds)
    return {
        "survivor_quarters": survivor_quarters,
        "survivor_quarters_red": survivor_quarters_red,
        "quarter_false_alarm_rate": survivor_quarters_red / survivor_quarters if survivor_quarters else 0.0,
        "rule_red_survivor": dict(rule_red_survivor),
        "rule_red_failure_quarters": dict(rule_red_failure_quarters),
        "failure_quarters": failure_quarters,
    }


def format_diagnosis(d: dict, name: str) -> str:
    lines = [
        f"{name}",
        f"  survivor bank-quarters: {d['survivor_quarters']}, with a red flag: {d['survivor_quarters_red']} "
        f"(quarter false alarm rate {d['quarter_false_alarm_rate']:.1%})",
        f"  red flags on survivors, by rule (bank-quarters):",
    ]
    for rule in RULE_NAMES:
        n = d["rule_red_survivor"].get(rule, 0)
        if n:
            lines.append(f"    {rule:<55} {n:>8}  ({n / max(d['survivor_quarters'], 1):.2%} of survivor quarters)")
    lines.append(f"  red flags in failing banks' pre-failure quarters, by rule:")
    for rule in RULE_NAMES:
        n = d["rule_red_failure_quarters"].get(rule, 0)
        if n:
            lines.append(f"    {rule:<55} {n:>8}")
    return "\n".join(lines) + "\n"


def run(warehouse_file: Path, reports_dir: Path) -> str:
    import duckdb

    from credit_risk.scorecard.labels import build_observations
    from credit_risk.scorecard.panel import load_panel
    from credit_risk.exposure.counterparties import fit_grader
    from credit_risk.warning.rules import peer_thresholds
    from credit_risk.warning.run_warning import WINDOWS, build_rows

    con = duckdb.connect(str(warehouse_file), read_only=True)
    try:
        panel, failures = load_panel(con, view="clean_scorecard_inputs")
        observations = build_observations(panel, failures, data_end=max(d for _, d, _ in panel))
        pd_of, scale = fit_grader(observations)
        rows = build_rows(con, pd_of, scale, panel)
    finally:
        con.close()
    parts = ["Diagnosis of the early-warning back-test (read-only; thresholds unchanged).", ""]
    for name, (start, end) in WINDOWS.items():
        quarters = {r.report_date for rs in rows.values() for r in rs if start <= r.report_date <= end}
        peers = {q: peer_thresholds([r for rs in rows.values() for r in rs if r.report_date == q]) for q in quarters}
        parts.append(format_diagnosis(diagnose(rows, failures, start, end, peers), name))
    text = "\n".join(parts) + "\n"
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "warning_diagnosis.txt").write_text(text, encoding="utf-8")
    return text


def main() -> int:
    from credit_risk.config import ProjectPaths

    paths = ProjectPaths.default()
    if not paths.warehouse_file.exists():
        print(f"Warehouse not found at {paths.warehouse_file}. Run make load first.")
        return 1
    print(run(paths.warehouse_file, paths.root / "reports"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
