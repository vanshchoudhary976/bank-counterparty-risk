from datetime import date

from credit_risk.warning.diagnose import RULE_NAMES, diagnose, format_diagnosis
from credit_risk.warning.rules import PeerThresholds, Row

PEERS = PeerThresholds(tier1_p25=0.08, ltd_p75=0.95)


def test_survivor_red_flag_is_counted_by_rule():
    rows = {1: [Row(1, date(2009, 3, 31), 0.05, 0.8, 3, 100.0), Row(1, date(2009, 6, 30), 0.05, 0.8, 3, 100.0)]}
    peers = {d: PEERS for d in (date(2009, 3, 31), date(2009, 6, 30))}
    d = diagnose(rows, {}, date(2009, 1, 1), date(2009, 12, 31), peers)
    assert d["survivor_quarters"] == 2
    assert d["survivor_quarters_red"] == 2
    assert d["rule_red_survivor"]["tier1 below floor"] == 2
    assert d["quarter_false_alarm_rate"] == 1.0


def test_format_lists_only_rules_that_fired():
    text = format_diagnosis({"survivor_quarters": 1, "survivor_quarters_red": 0, "quarter_false_alarm_rate": 0.0,
                             "rule_red_survivor": {}, "rule_red_failure_quarters": {}, "failure_quarters": 0}, "x")
    assert "tier1 below floor" not in text
    assert set(RULE_NAMES) >= {"tier1 below floor"}
