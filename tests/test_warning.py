from datetime import date

from credit_risk.warning.backtest import backtest
from credit_risk.warning.rules import PeerThresholds, Row, colour, evaluate


QUARTER_END = {1: (3, 31), 2: (6, 30), 3: (9, 30), 4: (12, 31)}


def _row(cert, y, q, tier1=0.10, ltd=0.8, grade=3, assets=100.0):
    m, d = QUARTER_END[q]
    return Row(cert=cert, report_date=date(y, m, d), tier1=tier1, ltd=ltd, grade=grade, assets=assets)


PEERS = PeerThresholds(tier1_p25=0.08, ltd_p75=0.95)


def test_healthy_bank_fires_nothing():
    hist = [_row(1, 2010, q) for q in range(1, 5)]
    assert colour(evaluate(hist, PEERS)) == "green"


def test_tier1_below_floor_is_red_and_below_peer_quartile_is_amber():
    assert colour(evaluate([_row(1, 2010, 1, tier1=0.05)], PEERS)) == "red"
    assert colour(evaluate([_row(1, 2010, 1, tier1=0.07)], PEERS)) == "amber"


def test_loans_to_deposits_rising_four_quarters_above_100_is_red():
    ltds = [0.9, 1.0, 1.05, 1.1, 1.2]
    hist = [_row(1, 2010, (i % 4) + 1, ltd=v) for i, v in enumerate(ltds)]
    assert ("loans to deposits above 100% and rising four quarters", "red") in evaluate(hist, PEERS)


def test_downgrade_one_notch_is_amber_two_notches_is_red():
    one = [_row(1, 2010, 1, grade=3), _row(1, 2010, 2, grade=4)]
    two = [_row(1, 2010, 1, grade=3), _row(1, 2010, 2, grade=5)]
    assert colour(evaluate(one, PEERS)) == "amber"
    assert colour(evaluate(two, PEERS)) == "red"


def test_grade_eight_is_red_even_without_a_downgrade():
    hist = [_row(1, 2010, 1, grade=8), _row(1, 2010, 2, grade=8)]
    assert colour(evaluate(hist, PEERS)) == "red"


def test_asset_growth_above_40_with_falling_capital_is_red():
    hist = [_row(1, 2009, 1, tier1=0.10, assets=100.0)]
    hist += [_row(1, 2009, 2, tier1=0.09, assets=110.0)]
    hist += [_row(1, 2009, 3, tier1=0.09, assets=120.0)]
    hist += [_row(1, 2009, 4, tier1=0.09, assets=130.0)]
    hist += [_row(1, 2010, 1, tier1=0.09, assets=145.0)]
    assert ("asset growth above 40% with falling capital", "red") in evaluate(hist, PEERS)


def test_backtest_counts_early_warning_and_misses():
    peers = {d: PEERS for d in {date(2009, 3, 31), date(2009, 6, 30), date(2009, 9, 30), date(2009, 12, 31),
                                date(2010, 3, 31), date(2010, 6, 30)}}
    early = [_row(1, 2009, q, tier1=0.05) for q in (1, 2, 3, 4)]
    late = [_row(2, 2009, 1), _row(2, 2009, 2), _row(2, 2009, 3, tier1=0.05)]
    survivor = [_row(3, 2009, 1, tier1=0.05), _row(3, 2009, 2)]
    rows = {1: early, 2: late, 3: survivor}
    failures = {1: date(2010, 6, 30), 2: date(2009, 12, 31)}
    result = backtest(rows, failures, date(2009, 1, 1), date(2010, 6, 30), peers)
    assert result.failures == 2
    assert result.red_first_warning[1] >= 4
    assert result.survivors == 1 and result.survivors_with_red == 1
    assert result.false_alarm_rate == 1.0
