"""Week 3 (Module B part 1): labelled dataset, blueprint split, baseline and expert score results.

Only the development and validation sets are scored here. The out-of-time test set is counted but
not scored, so it stays untouched for Week 4, as the blueprint requires.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from credit_risk.scorecard.baseline import fit_single_ratio_baseline
from credit_risk.scorecard.evaluation import auc
from credit_risk.scorecard.expert import ExpertScore
from credit_risk.scorecard.labels import Observation
from credit_risk.scorecard.split import (
    SetCounts,
    blueprint_split,
    check_development_events,
    check_every_set_has_rows,
)

BASELINE_RATIO = "tier1_leverage"
BASELINE_TARGET_SHARE = 0.10


@dataclass(frozen=True)
class Week3Results:
    counts: list[SetCounts]
    baseline_ratio: str
    baseline_threshold: float
    baseline_flag_share_validation: float
    baseline_auc_validation: float
    expert_auc_validation: float


def run_week3(observations: Sequence[Observation]) -> Week3Results:
    split = blueprint_split(list(observations))
    check_every_set_has_rows(split)
    check_development_events(split)
    dev_features = [o.features for o in split.development]
    val = [o for o in split.validation if o.features.get(BASELINE_RATIO) is not None]

    baseline = fit_single_ratio_baseline(dev_features, BASELINE_RATIO, BASELINE_TARGET_SHARE)
    val_labels = [o.label for o in val]
    baseline_scores = [baseline.risk_score(o.features) for o in val]
    flagged_share = sum(1 for o in val if baseline.flags(o.features)) / len(val)

    expert = ExpertScore().fit(dev_features)
    expert_rows = [(expert.score(o.features), o.label) for o in split.validation]
    expert_rows = [(s, y) for s, y in expert_rows if s is not None]

    return Week3Results(
        counts=split.counts(),
        baseline_ratio=baseline.ratio,
        baseline_threshold=baseline.threshold,
        baseline_flag_share_validation=flagged_share,
        baseline_auc_validation=auc(baseline_scores, val_labels),
        expert_auc_validation=auc([s for s, _ in expert_rows], [y for _, y in expert_rows]),
    )


def format_week3(results: Week3Results) -> str:
    lines = ["Week 3 (Module B part 1), blueprint split. Test set not scored.", ""]
    lines.append("Sets and event counts:")
    for c in results.counts:
        lines.append(f"  {c.name:<12} {c.start_year} to {c.end_year}: {c.bank_quarters} bank-quarters, {c.events} events")
    lines += [
        "",
        f"Single-ratio baseline ({results.baseline_ratio}): threshold {results.baseline_threshold:.4f}, "
        f"flags {results.baseline_flag_share_validation:.1%} of validation banks",
        f"  validation AUC: {results.baseline_auc_validation:.3f}",
        f"Expert CAMELS score: validation AUC {results.expert_auc_validation:.3f}",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    from datetime import date
    from pathlib import Path

    import duckdb

    from credit_risk.config import ProjectPaths
    from credit_risk.scorecard.labels import build_observations
    from credit_risk.scorecard.panel import load_panel

    warehouse = ProjectPaths.default().warehouse_file
    if not warehouse.exists():
        print(f"Warehouse not found at {warehouse}. Run make load first.")
        return 1
    con = duckdb.connect(str(warehouse), read_only=True)
    try:
        panel, failures = load_panel(con)
    finally:
        con.close()
    data_end: date = max(report_date for _, report_date, _ in panel)
    observations = build_observations(panel, failures, data_end=data_end)
    print(format_week3(run_week3(observations)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
