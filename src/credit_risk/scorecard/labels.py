"""Failure labels and the modelling panel.

Definitions (recorded in docs/scorecard.md):
- Only quarter-end report dates are used. Call Reports are filed for quarter-ends.
- A bank-quarter is labelled 1 if the bank fails within 12 months after its report date
  (four quarters), otherwise 0.
- A bank-quarter is dropped if the bank had already failed on or before its report date,
  because it cannot be a survivor at that point.
- A bank-quarter is dropped if the data ends less than 12 months after it, because we cannot
  yet tell whether that bank would have failed. Keeping it would wrongly label it 0.
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date
from typing import Iterable, Mapping, Optional

HORIZON_MONTHS = 12
QUARTER_END_MONTHS = (3, 6, 9, 12)


def is_quarter_end(report_date: date) -> bool:
    """True for 31 March, 30 June, 30 September and 31 December."""
    last_day = calendar.monthrange(report_date.year, report_date.month)[1]
    return report_date.month in QUARTER_END_MONTHS and report_date.day == last_day


def months_between(start: date, end: date) -> int:
    """Whole calendar months from start's month to end's month (end later means positive)."""
    return (end.year - start.year) * 12 + (end.month - start.month)


def label_failure(report_date: date, failure_date: Optional[date], horizon_months: int = HORIZON_MONTHS) -> int:
    """1 if the failure falls 1 to horizon_months calendar months after report_date, else 0."""
    if failure_date is None:
        return 0
    months = months_between(report_date, failure_date)
    return 1 if 1 <= months <= horizon_months else 0


@dataclass(frozen=True)
class Observation:
    cert: int
    report_date: date
    features: Mapping[str, Optional[float]]
    label: int


def build_observations(
    rows: Iterable[tuple[int, date, Mapping[str, Optional[float]]]],
    failures: Mapping[int, date],
    data_end: date,
    horizon_months: int = HORIZON_MONTHS,
) -> list[Observation]:
    """Turn (cert, report_date, features) rows into labelled observations.

    failures maps cert to the date the bank failed. Rows are kept only if they are quarter-end
    dates, the bank was still operating on the report date, and the horizon is fully observed.
    """
    observations: list[Observation] = []
    for cert, report_date, features in rows:
        if not is_quarter_end(report_date):
            continue
        failure_date = failures.get(cert)
        if failure_date is not None and failure_date <= report_date:
            continue
        if months_between(report_date, data_end) < horizon_months:
            continue
        observations.append(
            Observation(
                cert=cert,
                report_date=report_date,
                features=dict(features),
                label=label_failure(report_date, failure_date, horizon_months),
            )
        )
    return observations


@dataclass(frozen=True)
class Split:
    train: list[Observation]
    test: list[Observation]


def out_of_time_split(observations: list[Observation], test_from_year: int) -> Split:
    """Train on report dates before test_from_year, test on report dates from that year on.

    Splitting by time mirrors how the model would be used: learn from the past, score the future.
    A random split would let the model see later years during training.
    """
    train = [o for o in observations if o.report_date.year < test_from_year]
    test = [o for o in observations if o.report_date.year >= test_from_year]
    if not train or not test:
        raise ValueError(f"both sides of the split need rows; train={len(train)}, test={len(test)}")
    if sum(o.label for o in train) == 0 or sum(o.label for o in test) == 0:
        raise ValueError("both sides of the split need at least one failure label")
    return Split(train=train, test=test)
