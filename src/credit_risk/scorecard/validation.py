"""Validation checks for the logistic scorecard that are not rank metrics.

- Sign check: every coefficient must point the way the economics says (blueprint: check every sign).
- Drop-one-year sensitivity: refit without each development year; large moves mean one year drives the model.
- Migration matrix: how banks move between grades one year later.
- Missed failures: failing banks the model rated among the safest grades, for the error review.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Callable, Mapping, Optional, Sequence

from credit_risk.scorecard.scale import GRADE_COUNT

# +1 means a higher value raises the probability of failure; -1 means it lowers it.
EXPECTED_SIGNS: dict[str, int] = {
    "equity_to_assets": -1,
    "tier1_leverage": -1,
    "allowance_to_loans": 1,
    "roa_annualised": -1,
    "loans_to_deposits": 1,
    "efficiency_ratio": 1,
}


def sign_mismatches(coefficients: Mapping[str, float]) -> list[str]:
    """Names of features whose coefficient is zero or points the wrong way. An empty list means all pass."""
    missing = set(EXPECTED_SIGNS) - set(coefficients)
    if missing:
        raise ValueError(f"no coefficient for {sorted(missing)}")
    return [name for name, expected in EXPECTED_SIGNS.items() if coefficients[name] * expected <= 0]


@dataclass(frozen=True)
class YearSensitivity:
    year: int
    max_abs_change: float
    sign_flips: tuple[str, ...]


def drop_one_year_sensitivity(
    rows: Sequence[tuple[int, list[float], int]],
    feature_names: Sequence[str],
    fit: Callable[[list[list[float]], list[int]], Mapping[str, float]],
) -> list[YearSensitivity]:
    """Refit with each development year left out, and report the largest coefficient move.

    rows are (report_year, standardised inputs, label). fit returns coefficients by feature name.
    """
    full = fit([z for _, z, _ in rows], [y for _, _, y in rows])
    results = []
    for year in sorted({yr for yr, _, _ in rows}):
        kept = [(z, y) for yr, z, y in rows if yr != year]
        coefficients = fit([z for z, _ in kept], [y for _, y in kept])
        change = max(abs(coefficients[n] - full[n]) for n in feature_names)
        flips = tuple(n for n in feature_names if coefficients[n] * full[n] < 0)
        results.append(YearSensitivity(year, change, flips))
    return results


def migration_matrix(pairs: Sequence[tuple[int, int]]) -> list[list[int]]:
    """Count of banks moving from grade i (row) to grade j (column), grades 1 to 10."""
    matrix = [[0] * GRADE_COUNT for _ in range(GRADE_COUNT)]
    for grade_from, grade_to in pairs:
        if not (1 <= grade_from <= GRADE_COUNT and 1 <= grade_to <= GRADE_COUNT):
            raise ValueError(f"grades must be between 1 and {GRADE_COUNT}, got {grade_from} and {grade_to}")
        matrix[grade_from - 1][grade_to - 1] += 1
    return matrix


def migration_row_shares(matrix: Sequence[Sequence[int]]) -> list[Optional[float]]:
    """Share of each starting grade that stays in the same grade one year later. None if the row is empty."""
    shares: list[Optional[float]] = []
    for i, row in enumerate(matrix):
        total = sum(row)
        shares.append(None if total == 0 else row[i] / total)
    return shares


@dataclass(frozen=True)
class MissedFailure:
    cert: int
    report_date: date
    probability: float
    grade: int


def missed_failures(
    records: Sequence[tuple[int, date, float, int, int]],
    safest_grade_limit: int = 3,
) -> list[MissedFailure]:
    """Failures the model placed in grades 1 to safest_grade_limit. Records are (cert, date, PD, grade, label).

    Sorted by PD, lowest first, so the most surprising misses come first.
    """
    found = [
        MissedFailure(cert, report_date, pd, grade)
        for cert, report_date, pd, grade, label in records
        if label == 1 and grade <= safest_grade_limit
    ]
    return sorted(found, key=lambda m: (m.probability, m.cert))
