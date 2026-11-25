"""Tests for Module D step 3: the scenario configuration file and its loader."""

from pathlib import Path

import pytest

from credit_risk.stress import scenarios as code
from credit_risk.stress.scenario_config import Assumptions, load, parse, validate_scenario
from credit_risk.stress.scenarios import Scenario

CONFIG = Path(__file__).resolve().parents[1] / "config" / "scenarios.yaml"


def valid_data():
    return {
        "assumptions": {"securities_share": 0.25, "securities_duration_years": 4.0, "sale_loss_rate": 0.03},
        "scenarios": [{"name": "Credit shock", "deposit_run": 0.0, "provision_share": 0.03, "rate_shock_bp": 0.0}],
    }


def test_config_file_scenarios_match_code():
    _, loaded = load(CONFIG)
    assert loaded == code.SCENARIOS


def test_config_file_assumptions_match_code():
    assumptions, _ = load(CONFIG)
    assert assumptions == Assumptions(
        securities_share=code.SECURITIES_SHARE,
        securities_duration_years=code.SECURITIES_DURATION,
        sale_loss_rate=code.SALE_LOSS_RATE,
    )


def test_parse_accepts_valid_data():
    assumptions, scenarios = parse(valid_data())
    assert assumptions.sale_loss_rate == 0.03
    assert scenarios[0].name == "Credit shock"


def test_parse_rejects_non_mapping():
    with pytest.raises(ValueError):
        parse(["not", "a", "mapping"])


def test_parse_rejects_missing_assumption():
    data = valid_data()
    del data["assumptions"]["sale_loss_rate"]
    with pytest.raises(ValueError, match="missing keys"):
        parse(data)


def test_parse_rejects_empty_scenario_list():
    data = valid_data()
    data["scenarios"] = []
    with pytest.raises(ValueError, match="non-empty"):
        parse(data)


def test_parse_rejects_missing_scenario_key():
    data = valid_data()
    del data["scenarios"][0]["provision_share"]
    with pytest.raises(ValueError, match="missing keys"):
        parse(data)


def test_parse_rejects_duplicate_names():
    data = valid_data()
    data["scenarios"].append(dict(data["scenarios"][0]))
    with pytest.raises(ValueError, match="duplicate"):
        parse(data)


def test_parse_rejects_deposit_run_above_one():
    data = valid_data()
    data["scenarios"][0]["deposit_run"] = 1.5
    with pytest.raises(ValueError, match="deposit_run"):
        parse(data)


def test_validate_rejects_negative_rate_shock():
    with pytest.raises(ValueError, match="rate_shock_bp"):
        validate_scenario(Scenario("Bad", 0.0, 0.0, -10.0))


def test_validate_rejects_empty_name():
    with pytest.raises(ValueError, match="name"):
        validate_scenario(Scenario("  ", 0.0, 0.0, 0.0))


def test_validate_accepts_valid_scenario():
    sc = Scenario("Good", 0.1, 0.02, 50.0)
    assert validate_scenario(sc) is sc
