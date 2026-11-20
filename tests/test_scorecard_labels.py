import math
from datetime import date

import pytest

from credit_risk.scorecard.labels import (
    build_observations,
    is_quarter_end,
    label_failure,
    months_between,
    out_of_time_split,
    Observation,
)


def test_is_quarter_end_accepts_only_last_day_of_quarter_months():
    assert is_quarter_end(date(2020, 3, 31))
    assert is_quarter_end(date(2020, 6, 30))
    assert is_quarter_end(date(2020, 9, 30))
    assert is_quarter_end(date(2020, 12, 31))
    assert not is_quarter_end(date(2020, 3, 30))
    assert not is_quarter_end(date(2020, 2, 29))  # February is not a quarter-end month


def test_months_between_counts_calendar_months():
    assert months_between(date(2020, 3, 31), date(2021, 3, 10)) == 12
    assert months_between(date(2020, 3, 31), date(2020, 4, 1)) == 1
    assert months_between(date(2020, 3, 31), date(2020, 1, 5)) == -2


def test_label_is_one_for_failure_within_four_quarters():
    assert label_failure(date(2020, 3, 31), date(2020, 4, 1)) == 1
    assert label_failure(date(2020, 3, 31), date(2021, 3, 31)) == 1


def test_label_is_zero_just_outside_the_horizon_and_when_never_failed():
    assert label_failure(date(2020, 3, 31), date(2021, 4, 1)) == 0
    assert label_failure(date(2020, 3, 31), None) == 0


def test_build_observations_applies_all_filters_and_labels():
    failures = {1: date(2020, 9, 15)}
    rows = [
        (1, date(2020, 3, 31), {"x": 1.0}),  # kept, fails 5 months later -> label 1
        (1, date(2020, 6, 30), {"x": 2.0}),  # kept, fails 2 months later -> label 1
        (1, date(2020, 9, 30), {"x": 3.0}),  # dropped: failure date is before this report date
        (1, date(2020, 3, 15), {"x": 4.0}),  # dropped: not a quarter-end
        (2, date(2020, 3, 31), {"x": 5.0}),  # kept, never fails -> label 0
        (2, date(2022, 6, 30), {"x": 6.0}),  # dropped: horizon runs past the end of the data
        (3, date(2021, 12, 31), {"x": 7.0}),  # kept: exactly 12 months before data end
    ]
    observations = build_observations(rows, failures, data_end=date(2022, 12, 31))
    got = [(o.cert, o.report_date, o.label) for o in observations]
    assert got == [
        (1, date(2020, 3, 31), 1),
        (1, date(2020, 6, 30), 1),
        (2, date(2020, 3, 31), 0),
        (3, date(2021, 12, 31), 0),
    ]


def test_observation_keeps_features_as_given():
    observations = build_observations(
        [(5, date(2019, 12, 31), {"equity_to_assets": None})], {}, data_end=date(2022, 1, 1)
    )
    assert observations[0].features == {"equity_to_assets": None}


def _obs(year, label):
    return Observation(cert=1, report_date=date(year, 12, 31), features={}, label=label)


def test_out_of_time_split_puts_earlier_years_in_train_and_later_in_test():
    observations = [_obs(2018, 0), _obs(2019, 1), _obs(2020, 0), _obs(2021, 1)]
    split = out_of_time_split(observations, test_from_year=2020)
    assert [o.report_date.year for o in split.train] == [2018, 2019]
    assert [o.report_date.year for o in split.test] == [2020, 2021]


def test_out_of_time_split_rejects_empty_side():
    with pytest.raises(ValueError, match="both sides"):
        out_of_time_split([_obs(2018, 0), _obs(2019, 1)], test_from_year=2030)


def test_out_of_time_split_rejects_side_without_failures():
    with pytest.raises(ValueError, match="at least one failure"):
        out_of_time_split([_obs(2018, 1), _obs(2019, 0), _obs(2020, 0)], test_from_year=2020)
