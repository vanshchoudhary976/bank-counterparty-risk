"""Blueprint split for Module B: development, validation and out-of-time test, by report year.

Dates come from the blueprint's Module B table:
- Development 2005 to 2010: fit the models.
- Validation 2011 to 2013: tune, calibrate, choose the master scale.
- Out-of-time test 2014 to 2022: final performance, used once (Week 4 only).
The 2022 Q4 to 2023 Q1 case study is kept out of all three sets.
"""

from __future__ import annotations

from dataclasses import dataclass

from credit_risk.scorecard.labels import Observation

DEVELOPMENT = (2005, 2010)
VALIDATION = (2011, 2013)
TEST = (2014, 2022)
MIN_EVENTS = 100  # blueprint: if a training window has fewer than about 100 events, widen it


@dataclass(frozen=True)
class SetCounts:
    name: str
    start_year: int
    end_year: int
    bank_quarters: int
    events: int


@dataclass(frozen=True)
class BlueprintSplit:
    development: list[Observation]
    validation: list[Observation]
    test: list[Observation]

    def counts(self) -> list[SetCounts]:
        rows = []
        for name, items, (start, end) in (
            ("development", self.development, DEVELOPMENT),
            ("validation", self.validation, VALIDATION),
            ("test", self.test, TEST),
        ):
            rows.append(SetCounts(name, start, end, len(items), sum(o.label for o in items)))
        return rows


def blueprint_split(observations: list[Observation]) -> BlueprintSplit:
    """Assign each observation to one of the three sets by its report year. Years outside them are dropped."""

    def in_range(obs: Observation, bounds: tuple[int, int]) -> bool:
        return bounds[0] <= obs.report_date.year <= bounds[1]

    split = BlueprintSplit(
        development=[o for o in observations if in_range(o, DEVELOPMENT)],
        validation=[o for o in observations if in_range(o, VALIDATION)],
        test=[o for o in observations if in_range(o, TEST)],
    )
    return split


def check_every_set_has_rows(split: BlueprintSplit) -> None:
    for counts in split.counts():
        if counts.bank_quarters == 0:
            raise ValueError(f"the {counts.name} set ({counts.start_year} to {counts.end_year}) has no rows")


def check_development_events(split: BlueprintSplit) -> None:
    """Blueprint rule: the development window needs about 100 events. If it doesn't, widen it and record why."""
    events = sum(o.label for o in split.development)
    if events < MIN_EVENTS:
        raise ValueError(f"development set has {events} failure events, fewer than {MIN_EVENTS}; widen the window")
