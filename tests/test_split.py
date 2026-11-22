from datetime import date

import pytest

from credit_risk.scorecard.labels import Observation
from credit_risk.scorecard.split import (
    CASE_STUDY,
    MIN_EVENTS,
    TEST,
    blueprint_split,
    check_development_events,
    check_every_set_has_rows,
)


def _obs(year, label, month=12, day=31):
    return Observation(cert=1, report_date=date(year, month, day), features={}, label=label)


def test_blueprint_years_go_to_the_right_sets():
    observations = [_obs(y, 0) for y in range(2005, 2023)]
    split = blueprint_split(observations)
    assert {o.report_date.year for o in split.development} == set(range(2005, 2011))
    assert {o.report_date.year for o in split.validation} == set(range(2011, 2014))
    assert {o.report_date.year for o in split.test} == set(range(2014, 2022))  # 2022 Q4 is the case study


def test_test_window_stops_at_2022_q3():
    split = blueprint_split([_obs(2022, 0, month=9, day=30), _obs(2022, 0, month=12, day=31)])
    assert len(split.test) == 1
    assert split.test[0].report_date == date(2022, 9, 30)
    assert TEST.end == date(2022, 9, 30)


def test_case_study_quarters_go_to_case_study_only():
    split = blueprint_split([_obs(2022, 1), _obs(2023, 1, month=3, day=31), _obs(2023, 0, month=6, day=30)])
    assert [o.report_date for o in split.case_study] == [date(2022, 12, 31), date(2023, 3, 31)]
    assert split.test == [] and split.validation == [] and split.development == []
    assert CASE_STUDY.start == date(2022, 12, 31)


def test_counts_report_rows_and_events_per_set():
    observations = [_obs(2006, 1), _obs(2006, 0), _obs(2012, 1), _obs(2015, 0)]
    observations += [_obs(2007, 1)] * MIN_EVENTS
    counts = {c.name: c for c in blueprint_split(observations).counts()}
    assert counts["development"].events == MIN_EVENTS + 1
    assert counts["validation"].events == 1
    assert counts["test"].bank_quarters == 1
    assert counts["case study"].bank_quarters == 0


def test_split_refuses_too_few_development_events():
    split = blueprint_split([_obs(2006, 1), _obs(2006, 0), _obs(2012, 1), _obs(2015, 0)])
    with pytest.raises(ValueError, match="fewer than"):
        check_development_events(split)


def test_enough_development_events_pass_the_check():
    split = blueprint_split([_obs(2006, 1)] * MIN_EVENTS + [_obs(2006, 0)])
    check_development_events(split)


def test_empty_modelling_set_is_refused_by_the_check():
    split = blueprint_split([_obs(2006, 1)] * MIN_EVENTS)
    with pytest.raises(ValueError, match="has no rows"):
        check_every_set_has_rows(split)
