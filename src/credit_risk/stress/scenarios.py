"""Module D step 1: stress scenarios applied to a bank's balance sheet, then re-scored.

Every shock here is an ASSUMPTION, stated in this file and printed in the report. The credit
shock is a proxy: non-current loans are not loaded, so provisions equal a share of net loans.
Securities are not loaded either, so the rate shock uses an assumed securities share and duration.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from credit_risk.scorecard.panel import RATIO_COLUMNS

SECURITIES_SHARE = 0.25  # assumption: share of assets held as securities
SECURITIES_DURATION = 4.0  # assumption: years
SALE_LOSS_RATE = 0.03  # assumption: loss when securities are sold to meet outflows


@dataclass(frozen=True)
class Snapshot:
    assets: float
    equity: float
    net_loans: float
    deposits: float
    net_income: float
    allowance: float
    tier1: float  # tier 1 leverage as a fraction, e.g. 0.09
    efficiency: float | None  # not shocked
    month: int  # report month, for annualising income


@dataclass(frozen=True)
class Scenario:
    name: str
    deposit_run: float  # share of deposits lost
    provision_share: float  # extra provisions as a share of net loans (credit proxy)
    rate_shock_bp: float  # parallel rate rise in basis points


SCENARIOS = (
    Scenario("Base", 0.0, 0.0, 0.0),
    Scenario("Deposit run", 0.15, 0.0, 0.0),
    Scenario("Credit shock", 0.0, 0.03, 0.0),
    Scenario("Rate shock", 0.0, 0.0, 200.0),
    Scenario("Combined (half strength)", 0.075, 0.015, 100.0),
)


def features(s: Snapshot) -> dict[str, float | None]:
    """The six scorecard ratios, with the same definitions as sql/03 and sql/04."""
    gross = s.net_loans + s.allowance
    return {
        "equity_to_assets": s.equity / s.assets,
        "tier1_leverage": s.tier1,
        "allowance_to_loans": s.allowance / gross if gross else None,
        "roa_annualised": (12.0 / s.month) * s.net_income / s.assets,
        "efficiency_ratio": s.efficiency,
        "loans_to_deposits": s.net_loans / s.deposits if s.deposits else None,
    }


def apply_scenario(s: Snapshot, sc: Scenario) -> Snapshot:
    outflow = sc.deposit_run * s.deposits
    sale_loss = SALE_LOSS_RATE * outflow
    provisions = sc.provision_share * s.net_loans
    unrealised = SECURITIES_SHARE * s.assets * SECURITIES_DURATION * (sc.rate_shock_bp / 10_000.0)
    equity = s.equity - sale_loss - provisions - unrealised
    return replace(
        s,
        assets=s.assets - outflow,
        deposits=s.deposits - outflow,
        net_loans=s.net_loans - provisions,
        allowance=s.allowance + provisions,
        net_income=s.net_income - sale_loss - provisions,
        equity=equity,
        tier1=s.tier1 + (equity - s.equity) / s.assets,  # RWA not shocked; capital change over assets
    )


def stressed_features(s: Snapshot, sc: Scenario) -> dict[str, float | None]:
    return features(apply_scenario(s, sc))


assert set(RATIO_COLUMNS) == set(features(Snapshot(1, 1, 1, 1, 0, 0, 0.1, None, 12)).keys())
