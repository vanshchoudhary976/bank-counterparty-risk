"""Module D step 2 runner: back-test the early-warning rules on 2008 to 2012 failures and on the 2023 cases."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from credit_risk.exposure.counterparties import fit_grader
from credit_risk.warning.backtest import backtest
from credit_risk.warning.rules import PeerThresholds, Row, peer_thresholds

WINDOWS = {
    "2008 to 2012 failures": (date(2008, 1, 1), date(2012, 12, 31)),
    "2023 cases": (date(2022, 1, 1), date(2023, 12, 31)),
}


def build_rows(con, pd_of, scale, panel) -> dict[int, list[Row]]:
    assets = {(int(c), d): a for c, d, a in con.execute("SELECT cert, report_date, total_assets FROM bank_financials").fetchall()}
    rows: dict[int, list[Row]] = {}
    for cert, d, feats in panel:
        if feats.get("tier1_leverage") is None or feats.get("loans_to_deposits") is None:
            continue
        if any(v is None for v in feats.values()) or assets.get((cert, d)) is None:
            continue
        rows.setdefault(cert, []).append(
            Row(cert=cert, report_date=d, tier1=float(feats["tier1_leverage"]), ltd=float(feats["loans_to_deposits"]),
                grade=scale.grade(pd_of(feats)), assets=float(assets[(cert, d)]))
        )
    return rows


def run(warehouse_file: Path, reports_dir: Path) -> str:
    import duckdb

    from credit_risk.scorecard.labels import build_observations
    from credit_risk.scorecard.panel import load_panel

    con = duckdb.connect(str(warehouse_file), read_only=True)
    try:
        panel, failures = load_panel(con, view="clean_scorecard_inputs")
        observations = build_observations(panel, failures, data_end=max(d for _, d, _ in panel))
        pd_of, scale = fit_grader(observations)
        rows = build_rows(con, pd_of, scale, panel)
    finally:
        con.close()

    lines = [
        "ILLUSTRATIVE back-test. Thresholds are fixed in credit_risk/warning/rules.py before this run.",
        "Caveat: grades come from a scorecard fitted on 2005 to 2010, so the 2008 to 2010 part of the test is in-sample.",
        "Not run: non-current loans and securities unrealised losses (not loaded).",
        "",
    ]
    for name, (start, end) in WINDOWS.items():
        peers: dict[date, PeerThresholds] = {}
        quarters = {r.report_date for rs in rows.values() for r in rs if start <= r.report_date <= end}
        for q in quarters:
            peers[q] = peer_thresholds([r for rs in rows.values() for r in rs if r.report_date == q])
        res = backtest(rows, failures, start, end, peers)
        lines.append(f"{name}: {res.failures} failures in window")
        lines.append(f"  share flagged red at least 4 quarters ahead: {res.share_flagged_early:.0%}")
        lines.append(f"  survivors: {res.survivors}, with any red warning: {res.survivors_with_red} "
                     f"(false alarm rate {res.false_alarm_rate:.1%})")
        for cert, why in res.misses:
            lines.append(f"  miss: cert {cert}: {why}")
        lines.append("")
    text = "\n".join(lines) + "\n"
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "warning_backtest.txt").write_text(text, encoding="utf-8")
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
