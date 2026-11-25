"""Blueprint split for Module B: development, validation, out-of-time test and the 2023 case study.

Dates come from the blueprint's Module B table, using report dates:
- Development 2005 to 2010: fit the models.
- Validation 2011 to 2013: tune, calibrate, choose the master scale.
- Out-of-time test 2014 to 2022 Q3: final performance, scored once (Week 4 only).
- Case study 2022 Q4 to 2023 Q1: Silicon Valley Bank, Signature, First Republic. Kept out of every other set.
The test window ends at 2022 Q3 so that the case study quarters do not overlap it.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from credit_risk.scorecard.labels import Observation


@dataclass(frozen=True)
class Window:
    label: str
    start: date
    end: date

    def contains(self, report_date: date) -> bool:
        return self.start <= report_date <= self.end


DEVELOPMENT = Window("development (2005 to 2010)", date(2005, 1, 1), date(2010, 12, 31))
VALIDATION = Window("validation (2011 to 2013)", date(2011, 1, 1), date(2013, 12, 31))
TEST = Window("test (2014 to 2022 Q3)", date(2014, 1, 1), date(2022, 9, 30))
CASE_STUDY = Window("case study (2022 Q4 to 2023 Q1)", date(2022, 12, 31), date(2023, 3, 31))
MIN_EVENTS = 100  # blueprint: if a training window has fewer than about 100 events, widen it


@dataclass(frozen=True)
class SetCounts:
    name: str
    label: str
    bank_quarters: int
    events: int


@dataclass(frozen=True)
class BlueprintSplit:
    development: list[Observation]
    validation: list[Observation]
    test: list[Observation]
    case_study: list[Observation]

    def counts(self) -> list[SetCounts]:
        rows = []
        for name, items, window in (
            ("development", self.development, DEVELOPMENT),
            ("validation", self.validation, VALIDATION),
            ("test", self.test, TEST),
            ("case study", self.case_study, CASE_STUDY),
        ):
            rows.append(SetCounts(name, window.label, len(items), sum(o.label for o in items)))
        return rows


def blueprint_split(observations: list[Observation]) -> BlueprintSplit:
    """Assign each observation to one set by its report date. Dates outside all four windows are dropped."""
    return BlueprintSplit(
        development=[o for o in observations if DEVELOPMENT.contains(o.report_date)],
        validation=[o for o in observations if VALIDATION.contains(o.report_date)],
        test=[o for o in observations if TEST.contains(o.report_date)],
        case_study=[o for o in observations if CASE_STUDY.contains(o.report_date)],
    )


def check_every_set_has_rows(split: BlueprintSplit) -> None:
    """The three modelling sets must each have rows. The case study is checked separately."""
    for counts in split.counts():
        if counts.name in ("development", "validation", "test") and counts.bank_quarters == 0:
            raise ValueError(f"the {counts.name} set ({counts.label}) has no rows")


def check_development_events(split: BlueprintSplit) -> None:
    """Blueprint rule: the development window needs about 100 events. If it doesn't, widen it and record why."""
    events = sum(o.label for o in split.development)
    if events < MIN_EVENTS:
        raise ValueError(f"development set has {events} failure events, fewer than {MIN_EVENTS}; widen the window")
