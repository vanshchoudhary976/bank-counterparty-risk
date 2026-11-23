"""Module D step 3: load and validate the stress scenarios and assumptions from config/scenarios.yaml. ILLUSTRATIVE.

The file is the readable record of every assumption. The tests check that it matches the values used in code,
so the two cannot drift apart silently.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from credit_risk.stress.scenarios import Scenario

REQUIRED_ASSUMPTIONS = ("securities_share", "securities_duration_years", "sale_loss_rate")
REQUIRED_SCENARIO_KEYS = ("name", "deposit_run", "provision_share", "rate_shock_bp")


@dataclass(frozen=True)
class Assumptions:
    securities_share: float
    securities_duration_years: float
    sale_loss_rate: float


def validate_scenario(sc: Scenario) -> Scenario:
    if not sc.name.strip():
        raise ValueError("scenario name must not be empty")
    if not 0.0 <= sc.deposit_run <= 1.0:
        raise ValueError(f"{sc.name}: deposit_run must be between 0 and 1, got {sc.deposit_run}")
    if not 0.0 <= sc.provision_share <= 1.0:
        raise ValueError(f"{sc.name}: provision_share must be between 0 and 1, got {sc.provision_share}")
    if sc.rate_shock_bp < 0:
        raise ValueError(f"{sc.name}: rate_shock_bp must not be negative, got {sc.rate_shock_bp}")
    return sc


def parse(data: Any) -> tuple[Assumptions, tuple[Scenario, ...]]:
    if not isinstance(data, dict):
        raise ValueError("scenario config must be a mapping with 'assumptions' and 'scenarios'")

    raw_assumptions = data.get("assumptions")
    if not isinstance(raw_assumptions, dict):
        raise ValueError("'assumptions' must be a mapping")
    missing = [k for k in REQUIRED_ASSUMPTIONS if k not in raw_assumptions]
    if missing:
        raise ValueError(f"assumptions missing keys: {missing}")
    assumptions = Assumptions(
        securities_share=float(raw_assumptions["securities_share"]),
        securities_duration_years=float(raw_assumptions["securities_duration_years"]),
        sale_loss_rate=float(raw_assumptions["sale_loss_rate"]),
    )
    if not 0.0 <= assumptions.securities_share <= 1.0:
        raise ValueError("securities_share must be between 0 and 1")
    if assumptions.securities_duration_years < 0:
        raise ValueError("securities_duration_years must not be negative")
    if not 0.0 <= assumptions.sale_loss_rate <= 1.0:
        raise ValueError("sale_loss_rate must be between 0 and 1")

    raw_scenarios = data.get("scenarios")
    if not isinstance(raw_scenarios, list) or not raw_scenarios:
        raise ValueError("'scenarios' must be a non-empty list")
    scenarios: list[Scenario] = []
    seen: set[str] = set()
    for item in raw_scenarios:
        if not isinstance(item, dict):
            raise ValueError("each scenario must be a mapping")
        missing = [k for k in REQUIRED_SCENARIO_KEYS if k not in item]
        if missing:
            raise ValueError(f"scenario missing keys: {missing}")
        sc = validate_scenario(
            Scenario(
                name=str(item["name"]),
                deposit_run=float(item["deposit_run"]),
                provision_share=float(item["provision_share"]),
                rate_shock_bp=float(item["rate_shock_bp"]),
            )
        )
        if sc.name in seen:
            raise ValueError(f"duplicate scenario name: {sc.name}")
        seen.add(sc.name)
        scenarios.append(sc)
    return assumptions, tuple(scenarios)


def load(path: Path) -> tuple[Assumptions, tuple[Scenario, ...]]:
    with open(path, encoding="utf-8") as fh:
        return parse(yaml.safe_load(fh))
