import pytest

from credit_risk.scorecard.panel import RATIO_COLUMNS
from credit_risk.stress.scenarios import SCENARIOS, Scenario, Snapshot, apply_scenario, features, stressed_features

BASE = Snapshot(assets=1000.0, equity=100.0, net_loans=600.0, deposits=800.0, net_income=10.0,
                allowance=10.0, tier1=0.10, efficiency=0.6, month=12)


def test_features_have_the_six_scorecard_ratios():
    assert set(features(BASE)) == set(RATIO_COLUMNS)


def test_base_scenario_leaves_features_unchanged():
    base = next(s for s in SCENARIOS if s.name == "Base")
    assert stressed_features(BASE, base) == features(BASE)


def test_deposit_run_raises_loans_to_deposits_and_shrinks_assets():
    sc = Scenario("run", 0.15, 0.0, 0.0)
    after = apply_scenario(BASE, sc)
    assert after.deposits == pytest.approx(800.0 * 0.85)
    assert after.assets == pytest.approx(1000.0 - 120.0)
    assert features(after)["loans_to_deposits"] > features(BASE)["loans_to_deposits"]


def test_credit_shock_cuts_equity_and_raises_allowance_ratio():
    sc = Scenario("credit", 0.0, 0.03, 0.0)
    after = apply_scenario(BASE, sc)
    assert after.equity < BASE.equity
    assert features(after)["allowance_to_loans"] > features(BASE)["allowance_to_loans"]


def test_rate_shock_cuts_capital_but_not_earnings():
    sc = Scenario("rate", 0.0, 0.0, 200.0)
    after = apply_scenario(BASE, sc)
    assert after.equity < BASE.equity
    assert after.net_income == BASE.net_income
    assert after.tier1 < BASE.tier1


def test_combined_is_worse_than_each_half_strength_shock_alone():
    combined = next(s for s in SCENARIOS if s.name.startswith("Combined"))
    eq_combined = apply_scenario(BASE, combined).equity
    eq_rate_half = apply_scenario(BASE, Scenario("r", 0.0, 0.0, 100.0)).equity
    assert eq_combined < eq_rate_half


def test_stress_never_improves_capital_ratio():
    for sc in SCENARIOS:
        assert apply_scenario(BASE, sc).equity <= BASE.equity + 1e-9
