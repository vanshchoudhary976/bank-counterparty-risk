"""Checks on the scorecard: discrimination (AUC) and whether grades order risk correctly."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


def auc(scores: Sequence[float], labels: Sequence[int]) -> float:
    """Probability that a randomly chosen failed bank scores higher risk than a survivor.

    Here scores are PDs (higher = riskier). 0.5 is no better than chance, 1.0 is perfect.
    Ties count half. Equivalent to the Mann-Whitney U statistic divided by n_bad x n_good.
    """
    if len(scores) != len(labels):
        raise ValueError("scores and labels must be the same length")
    n_bad = sum(1 for y in labels if y == 1)
    n_good = sum(1 for y in labels if y == 0)
    if n_bad == 0 or n_good == 0:
        raise ValueError("AUC needs both failures and survivors")

    order = sorted(range(len(scores)), key=lambda i: scores[i])
    rank_sum_bad = 0.0
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and scores[order[j + 1]] == scores[order[i]]:
            j += 1
        average_rank = (i + j) / 2 + 1  # ranks start at 1
        for k in range(i, j + 1):
            if labels[order[k]] == 1:
                rank_sum_bad += average_rank
        i = j + 1
    u = rank_sum_bad - n_bad * (n_bad + 1) / 2
    return u / (n_bad * n_good)


@dataclass(frozen=True)
class GradeRow:
    grade: int
    count: int
    failures: int
    failure_rate: float


def default_rate_by_grade(grades: Sequence[int], labels: Sequence[int]) -> list[GradeRow]:
    """Observed failure rate per grade, for grades that have at least one bank, in grade order."""
    if len(grades) != len(labels):
        raise ValueError("grades and labels must be the same length")
    counts: dict[int, int] = {}
    failures: dict[int, int] = {}
    for grade, label in zip(grades, labels):
        counts[grade] = counts.get(grade, 0) + 1
        failures[grade] = failures.get(grade, 0) + label
    return [
        GradeRow(grade=g, count=counts[g], failures=failures[g], failure_rate=failures[g] / counts[g])
        for g in sorted(counts)
    ]


def is_risk_ordered(rows: Sequence[GradeRow]) -> bool:
    """True if failure rates never fall as the grade number rises (grade 10 is the riskiest)."""
    return all(b.failure_rate >= a.failure_rate for a, b in zip(rows, rows[1:]))
