import pytest

from credit_risk.scorecard.baseline import SingleRatioBaseline, fit_single_ratio_baseline

DEV = [{"tier1_leverage": v / 100} for v in range(1, 101)]  # 0.01 to 1.00


def test_threshold_flags_the_target_share_of_development_banks():
    baseline = fit_single_ratio_baseline(DEV, "tier1_leverage", target_share=0.10)
    flagged = sum(1 for row in DEV if baseline.flags(row))
    assert flagged == pytest.approx(10, abs=1)


def test_low_ratio_is_flagged_and_high_ratio_is_not():
    baseline = SingleRatioBaseline(ratio="tier1_leverage", threshold=0.05)
    assert baseline.flags({"tier1_leverage": 0.03}) is True
    assert baseline.flags({"tier1_leverage": 0.09}) is False


def test_missing_value_is_not_flagged_and_has_no_score():
    baseline = SingleRatioBaseline(ratio="tier1_leverage", threshold=0.05)
    assert baseline.flags({"tier1_leverage": None}) is False
    assert baseline.risk_score({"tier1_leverage": None}) is None


def test_risk_score_is_higher_for_lower_ratio():
    baseline = SingleRatioBaseline(ratio="tier1_leverage", threshold=0.05)
    assert baseline.risk_score({"tier1_leverage": 0.02}) > baseline.risk_score({"tier1_leverage": 0.09})


def test_bad_target_share_is_rejected():
    with pytest.raises(ValueError):
        fit_single_ratio_baseline(DEV, "tier1_leverage", target_share=1.5)
