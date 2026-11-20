"""Turn a probability of default (PD) into a score, and PDs into 10 master-scale grades.

Score scaling (standard scorecard convention):
- Score = offset + factor x ln(good odds), where good odds = (1 - PD) / PD.
- factor = PDO / ln(2): the points needed to double the good odds.
- The offset is set so that base_odds gives base_score. Higher score = safer bank.

Master scale: 10 grades, grade 1 safest. Each grade is a band of PD with an upper limit.
The cut points are supplied by the caller, so they can be chosen and documented separately.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

GRADE_COUNT = 10
PD_FLOOR = 1e-9


@dataclass(frozen=True)
class ScoreScale:
    base_score: float = 600.0
    base_odds: float = 50.0  # good odds at base_score, i.e. 50 survivors per 1 failure
    pdo: float = 20.0  # points to double the good odds

    def __post_init__(self) -> None:
        if self.base_odds <= 0 or self.pdo <= 0:
            raise ValueError("base_odds and pdo must be positive")

    @property
    def factor(self) -> float:
        return self.pdo / math.log(2)

    @property
    def offset(self) -> float:
        return self.base_score - self.factor * math.log(self.base_odds)

    def score(self, pd: float) -> float:
        if not 0.0 <= pd <= 1.0:
            raise ValueError(f"PD must be between 0 and 1, got {pd}")
        pd = min(max(pd, PD_FLOOR), 1.0 - PD_FLOOR)
        good_odds = (1.0 - pd) / pd
        return self.offset + self.factor * math.log(good_odds)


def training_quantile_cutoffs(train_pds: Sequence[float], grade_count: int = GRADE_COUNT) -> tuple[float, ...]:
    """Cut-offs that put about the same number of TRAINING banks in each grade.

    Calculated only from training-period probabilities, so the test set never shapes the grades.
    Repeated values are kept: the model uses few distinct inputs, so many banks share one probability.
    A repeated cut-off leaves the grade between the two equal values empty, which the report shows.
    """
    if not train_pds:
        raise ValueError("need training probabilities to set cut-offs")
    ordered = sorted(train_pds)
    n = len(ordered)
    cutoffs = tuple(ordered[min(n - 1, k * n // grade_count)] for k in range(1, grade_count))
    if cutoffs[-1] >= 1.0 or cutoffs[0] <= 0.0:
        raise ValueError("training cut-offs must lie strictly between 0 and 1")
    return cutoffs


@dataclass(frozen=True)
class MasterScale:
    """Ten grades from PD upper limits. cutoffs must hold nine values in (0, 1), not decreasing."""

    cutoffs: tuple[float, ...]

    def __post_init__(self) -> None:
        if len(self.cutoffs) != GRADE_COUNT - 1:
            raise ValueError(f"need {GRADE_COUNT - 1} cut-offs for {GRADE_COUNT} grades, got {len(self.cutoffs)}")
        if any(not 0.0 < c < 1.0 for c in self.cutoffs):
            raise ValueError("every cut-off must be between 0 and 1")
        if any(b < a for a, b in zip(self.cutoffs, self.cutoffs[1:])):
            raise ValueError("cut-offs must not decrease")

    def grade(self, pd: float) -> int:
        """Grade 1 (lowest PD) to 10 (highest PD)."""
        if not 0.0 <= pd <= 1.0:
            raise ValueError(f"PD must be between 0 and 1, got {pd}")
        for index, limit in enumerate(self.cutoffs):
            if pd <= limit:
                return index + 1
        return GRADE_COUNT
