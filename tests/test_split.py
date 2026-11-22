from datetime import date

import pytest

from credit_risk.scorecard.labels import Observation
from credit_risk.scorecard.split import (
    MIN_EVENTS,
    blueprint_split,
    check_development_events,
    check_every_set_has_rows,
)


def _obs(year, label):
    return Observation(cert=1, report_date=date(year, 12, 31), features={}, label=label)


def test_blueprint_years_go_to_the_right_sets():
    observations = [_obs(y, 0) for y in range(2005, 2024)]
    split = blueprint_split(observations)
    assert {o.report_date.year for o in split.development} == set(range(2005, 2011))
    assert {o.report_date.year for o in split.validation} == set(range(2011, 2014))
    assert {o.report_date.year for o in split.test} == set(range(2014, 2023))


def test_case_study_years_are_left_out_of_every_set():
    split = blueprint_split([_obs(2023, 1), _obs(2005, 0), _obs(2012, 0), _obs(2015, 0)])
    assert all(o.report_date.year != 2023 for o in split.development + split.validation + split.test)


def test_counts_report_rows_and_events_per_set():
    observations = [_obs(2006, 1), _obs(2006, 0), _obs(2012, 1), _obs(2015, 0)]
    observations += [_obs(2007, 1)] * (MIN_EVENTS)
    counts = {c.name: c for c in blueprint_split(observations).counts()}
    assert counts["development"].events == MIN_EVENTS + 1
    assert counts["validation"].events == 1
    assert counts["test"].bank_quarters == 1


def test_split_refuses_too_few_development_events():
    split = blueprint_split([_obs(2006, 1), _obs(2006, 0), _obs(2012, 1), _obs(2015, 0)])
    with pytest.raises(ValueError, match="fewer than"):
        check_development_events(split)


def test_enough_development_events_pass_the_check():
    split = blueprint_split([_obs(2006, 1)] * MIN_EVENTS + [_obs(2006, 0)])
    check_development_events(split)


def test_empty_set_is_refused_by_the_check():
    split = blueprint_split([_obs(2006, 1)] * MIN_EVENTS)
    with pytest.raises(ValueError, match="has no rows"):
        check_every_set_has_rows(split)
