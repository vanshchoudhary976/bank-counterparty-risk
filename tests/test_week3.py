from datetime import date
import random

from credit_risk.scorecard.labels import Observation
from credit_risk.scorecard.week3 import run_week3


def _synthetic():
    rng = random.Random(7)  # fixed seed so the test is repeatable
    observations = []
    for year in range(2005, 2023):
        for cert in range(1, 121):
            failing = cert % 6 == 0
            base = 0.06 if failing else 0.10
            features = {
                "tier1_leverage": base + rng.uniform(-0.01, 0.01),
                "equity_to_assets": base + rng.uniform(-0.01, 0.01),
                "allowance_to_loans": 0.01 + rng.uniform(-0.002, 0.002),
                "roa_annualised": (-0.005 if failing else 0.008) + rng.uniform(-0.002, 0.002),
                "loans_to_deposits": (0.9 if failing else 0.7) + rng.uniform(-0.05, 0.05),
                "efficiency_ratio": (0.7 if failing else 0.5) + rng.uniform(-0.05, 0.05),
            }
            observations.append(Observation(cert, date(year, 12, 31), features, 1 if failing else 0))
    return observations


def test_week3_reports_counts_and_validation_results_only():
    results = run_week3(_synthetic())
    counts = {c.name: c for c in results.counts}
    assert counts["development"].events > 0 and counts["validation"].events > 0
    assert counts["test"].bank_quarters > 0
    assert 0.0 <= results.baseline_auc_validation <= 1.0
    assert 0.0 <= results.expert_auc_validation <= 1.0


def test_expert_score_beats_chance_on_synthetic_data():
    assert run_week3(_synthetic()).expert_auc_validation > 0.8


def test_report_prints_counts_and_both_benchmarks():
    from credit_risk.scorecard.week3 import format_week3

    text = format_week3(run_week3(_synthetic()))
    for phrase in ("development", "validation", "test", "baseline", "Expert CAMELS", "Test set not scored"):
        assert phrase in text
