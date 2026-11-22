from credit_risk.stress.run_stress import stressed_snap_equity_change
from credit_risk.stress.scenarios import SCENARIOS, Snapshot

BASE = Snapshot(assets=1000.0, equity=100.0, net_loans=600.0, deposits=800.0, net_income=10.0,
                allowance=10.0, tier1=0.10, efficiency=0.6, month=12)


def test_tier1_change_is_zero_for_base_and_negative_under_stress():
    base = next(s for s in SCENARIOS if s.name == "Base")
    assert stressed_snap_equity_change(BASE, base) == 0.0
    rate = next(s for s in SCENARIOS if s.name == "Rate shock")
    assert stressed_snap_equity_change(BASE, rate) < 0
