"""Validation metrics for the scorecard. Scores are probabilities of failure: higher = riskier.

- Gini and KS measure how well the scores separate failures from survivors.
- Decile table shows whether the riskiest banks really fail most, and how predicted and observed rates compare.
- PSI measures whether an input has drifted between two periods.
- Spearman and riskiest-decile overlap compare the scorecard with the expert score.
"""

from __future__ import annotations

import math
from bisect import bisect_left
from dataclasses import dataclass
from typing import Sequence

from credit_risk.scorecard.evaluation import auc

PSI_FLOOR = 1e-6


def gini(scores: Sequence[float], labels: Sequence[int]) -> float:
    """Gini = 2 x AUC - 1. Same information as AUC, on a scale from 0 (random) to 1 (perfect)."""
    return 2.0 * auc(scores, labels) - 1.0


def ks_statistic(scores: Sequence[float], labels: Sequence[int]) -> float:
    """Largest gap, over all cut-offs, between the share of failures and the share of survivors at or above it."""
    if len(scores) != len(labels):
        raise ValueError("scores and labels must be the same length")
    n_bad = sum(1 for y in labels if y == 1)
    n_good = len(labels) - n_bad
    if n_bad == 0 or n_good == 0:
        raise ValueError("KS needs both failures and survivors")
    pairs = sorted(zip(scores, labels), key=lambda p: p[0], reverse=True)
    best = 0.0
    bad_seen = 0
    good_seen = 0
    i = 0
    while i < len(pairs):
        value = pairs[i][0]
        j = i
        while j < len(pairs) and pairs[j][0] == value:
            if pairs[j][1] == 1:
                bad_seen += 1
            else:
                good_seen += 1
            j += 1
        best = max(best, abs(bad_seen / n_bad - good_seen / n_good))
        i = j
    return best


@dataclass(frozen=True)
class DecileRow:
    decile: int  # 1 = riskiest tenth of bank-quarters, 10 = safest
    count: int
    failures: int
    mean_predicted: float
    observed_rate: float


def decile_table(pds: Sequence[float], labels: Sequence[int], deciles: int = 10) -> list[DecileRow]:
    """Split bank-quarters into equal groups from riskiest to safest, and compare predicted with observed."""
    if len(pds) != len(labels):
        raise ValueError("pds and labels must be the same length")
    if len(pds) < deciles:
        raise ValueError(f"need at least {deciles} rows for a {deciles}-group table")
    pairs = sorted(zip(pds, labels), key=lambda p: p[0], reverse=True)
    n = len(pairs)
    rows = []
    for d in range(deciles):
        chunk = pairs[d * n // deciles:(d + 1) * n // deciles]
        count = len(chunk)
        failures = sum(label for _, label in chunk)
        mean_predicted = sum(pd for pd, _ in chunk) / count
        rows.append(DecileRow(d + 1, count, failures, mean_predicted, failures / count))
    return rows


def share_of_failures_in_riskiest_decile(rows: Sequence[DecileRow]) -> float:
    total = sum(r.failures for r in rows)
    if total == 0:
        raise ValueError("no failures in the table")
    return rows[0].failures / total


def psi(expected: Sequence[float], actual: Sequence[float], bins: int = 10) -> float:
    """Population Stability Index. Bins come from the expected (development) distribution.

    Rule of thumb: below 0.10 stable, 0.10 to 0.25 some shift, above 0.25 major shift.
    """
    if not expected or not actual:
        raise ValueError("PSI needs values in both samples")
    ordered = sorted(expected)
    n = len(ordered)
    edges = sorted({ordered[k * n // bins] for k in range(1, bins)})

    def histogram(values: Sequence[float]) -> list[int]:
        counts = [0] * (len(edges) + 1)
        for v in values:
            counts[bisect_left(edges, v)] += 1
        return counts

    expected_counts = histogram(expected)
    actual_counts = histogram(actual)
    total = 0.0
    for e_count, a_count in zip(expected_counts, actual_counts):
        e_share = max(e_count / len(expected), PSI_FLOOR)
        a_share = max(a_count / len(actual), PSI_FLOOR)
        total += (a_share - e_share) * math.log(a_share / e_share)
    return total


def _average_ranks(values: Sequence[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        average = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[order[k]] = average
        i = j + 1
    return ranks


def spearman(a: Sequence[float], b: Sequence[float]) -> float:
    """Rank correlation: 1 means the two scores order the banks identically, 0 means no relationship."""
    if len(a) != len(b):
        raise ValueError("the two samples must be the same length")
    if len(a) < 2:
        raise ValueError("need at least two pairs")
    ra = _average_ranks(a)
    rb = _average_ranks(b)
    n = len(a)
    mean_a = sum(ra) / n
    mean_b = sum(rb) / n
    cov = sum((x - mean_a) * (y - mean_b) for x, y in zip(ra, rb))
    var_a = sum((x - mean_a) ** 2 for x in ra)
    var_b = sum((y - mean_b) ** 2 for y in rb)
    if var_a == 0 or var_b == 0:
        raise ValueError("a constant score has no rank correlation")
    return cov / math.sqrt(var_a * var_b)


def riskiest_overlap(scores_a: Sequence[float], scores_b: Sequence[float], share: float = 0.10) -> float:
    """Share of the riskiest `share` of banks under score A that are also in the riskiest under score B.

    Ties are broken by position in the list, so the result is repeatable.
    """
    if len(scores_a) != len(scores_b):
        raise ValueError("the two score lists must be the same length")
    n = len(scores_a)
    k = max(1, round(share * n))
    top_a = set(sorted(range(n), key=lambda i: scores_a[i], reverse=True)[:k])
    top_b = set(sorted(range(n), key=lambda i: scores_b[i], reverse=True)[:k])
    return len(top_a & top_b) / k
