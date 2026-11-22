import pytest

from credit_risk.scorecard.expert import (
    EXPERT_RATIOS,
    ExpertScore,
    expert_weights_total,
    risk_percentile,
)

DEV = [
    {"tier1_leverage": 0.05 + 0.01 * i, "equity_to_assets": 0.05 + 0.01 * i,
     "allowance_to_loans": 0.01 + 0.001 * i, "roa_annualised": -0.01 + 0.002 * i,
     "loans_to_deposits": 0.5 + 0.01 * i, "efficiency_ratio": 0.4 + 0.01 * i}
    for i in range(10)
]


def test_weights_add_to_one_and_match_the_blueprint_areas():
    assert expert_weights_total() == pytest.approx(1.0)
    by_name = {name: weight for name, _, weight in EXPERT_RATIOS}
    assert by_name["tier1_leverage"] + by_name["equity_to_assets"] == pytest.approx(0.30)  # capital
    assert by_name["allowance_to_loans"] == pytest.approx(0.25)  # asset quality
    assert by_name["roa_annualised"] == pytest.approx(0.15)  # earnings
    assert by_name["loans_to_deposits"] == pytest.approx(0.20)  # liquidity
    assert by_name["efficiency_ratio"] == pytest.approx(0.10)  # efficiency


def test_percentile_direction_is_correct():
    reference = [1, 2, 3, 4]
    assert risk_percentile(4, reference, higher_is_riskier=True) == pytest.approx(1.0)  # riskiest
    assert risk_percentile(1, reference, higher_is_riskier=True) == pytest.approx(0.25)
    assert risk_percentile(1, reference, higher_is_riskier=False) == pytest.approx(1.0)  # lowest is riskiest


def test_riskier_bank_scores_higher():
    expert = ExpertScore().fit(DEV)
    safe = {"tier1_leverage": 0.14, "equity_to_assets": 0.14, "allowance_to_loans": 0.02,
            "roa_annualised": 0.016, "loans_to_deposits": 0.55, "efficiency_ratio": 0.42}
    risky = {"tier1_leverage": 0.05, "equity_to_assets": 0.05, "allowance_to_loans": 0.01,
             "roa_annualised": -0.008, "loans_to_deposits": 0.95, "efficiency_ratio": 0.68}
    assert expert.score(risky) > expert.score(safe)


def test_missing_ratio_gives_no_score_not_a_guess():
    expert = ExpertScore().fit(DEV)
    features = dict(DEV[0])
    features["roa_annualised"] = None
    assert expert.score(features) is None


def test_score_needs_fitting_first():
    with pytest.raises(ValueError, match="fit"):
        ExpertScore().score(DEV[0])
