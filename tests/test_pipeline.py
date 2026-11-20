from datetime import date

import pytest

from credit_risk.scorecard.labels import Observation
from credit_risk.scorecard.pipeline import format_report, run_scorecard


def _synthetic_observations():
    """Ten years, 30 banks. Every sixth bank is a failure with low equity to assets."""
    observations = []
    for year in range(2011, 2023):
        for cert in range(1, 31):
            failing = cert % 6 == 0
            observations.append(
                Observation(
                    cert=cert,
                    report_date=date(year, 12, 31),
                    features={
                        "equity_to_assets": (0.05 + 0.001 * (cert % 5)) if failing else (0.10 + 0.002 * (cert % 7)),
                        "loans_to_deposits": 0.70 + 0.01 * (cert % 4),
                        "roa_annualised": 0.005 + 0.0005 * (cert % 3),
                    },
                    label=1 if failing else 0,
                )
            )
    return observations


def test_pipeline_separates_failures_out_of_time():
    result = run_scorecard(_synthetic_observations(), test_from_year=2019)
    assert result.test_auc > 0.95
    assert result.train_rows == 8 * 30
    assert result.test_rows == 4 * 30
    assert result.test_failures > 0


def test_higher_equity_means_lower_failure_risk_in_the_model():
    result = run_scorecard(_synthetic_observations(), test_from_year=2019)
    coefficients = dict(zip(result.model.feature_names, result.model.coefficients))
    assert coefficients["equity_to_assets"] < 0


def test_grade_counts_cover_every_test_bank():
    result = run_scorecard(_synthetic_observations(), test_from_year=2019)
    assert sum(row.count for row in result.grade_rows) == result.test_rows
    assert len(result.cutoffs) == 9
    assert list(result.cutoffs) == sorted(result.cutoffs)


def test_report_mentions_the_key_results():
    text = format_report(run_scorecard(_synthetic_observations(), test_from_year=2019))
    for phrase in ("Out-of-time AUC", "Information value", "Grades on test set", "Failure rates rise"):
        assert phrase in text


def test_pipeline_refuses_a_split_with_no_test_failures():
    observations = [o for o in _synthetic_observations() if o.report_date.year < 2019 or o.label == 0]
    with pytest.raises(ValueError, match="at least one failure"):
        run_scorecard(observations, test_from_year=2019)
