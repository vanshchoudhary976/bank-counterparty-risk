"""Weight of evidence (WoE) and information value (IV) for one ratio.

WoE for a bin = ln( share of good banks in the bin / share of bad banks in the bin ).
Good means label 0 (survived), bad means label 1 (failed within the horizon).
Positive WoE: the bin holds more survivors than its share of failures, so it is safer.

IV = sum over bins of (share of good - share of bad) x WoE. Rough reading used in practice:
below 0.02 weak, 0.1 to 0.3 medium, above 0.3 strong. Treat these as rules of thumb.

Missing values get their own bin, so a missing ratio is not silently treated as a typical value.
"""

from __future__ import annotations

import math
from bisect import bisect_right
from dataclasses import dataclass
from typing import Optional, Sequence

MISSING_LABEL = "missing"
SMOOTHING = 0.5  # added to every bin count so that no share is zero and WoE stays finite


@dataclass(frozen=True)
class WoeBin:
    label: str
    good: int
    bad: int
    woe: float


@dataclass(frozen=True)
class WoeTable:
    cuts: tuple[float, ...]
    bins: tuple[WoeBin, ...]
    information_value: float

    def woe_for(self, value: Optional[float]) -> float:
        """WoE of the bin a new value falls into. Used when scoring banks."""
        index = bin_index(value, self.cuts)
        return self.bins[index].woe if index is not None else self.bins[-1].woe


def quantile_cuts(values: Sequence[Optional[float]], n_bins: int) -> tuple[float, ...]:
    """Cut points that split the non-missing values into about n_bins equal-count groups.

    Duplicate cut points are removed, so a ratio with few distinct values gets fewer bins.
    """
    if n_bins < 2:
        raise ValueError("n_bins must be at least 2")
    present = sorted(v for v in values if v is not None)
    if not present:
        raise ValueError("no non-missing values to bin")
    cuts: list[float] = []
    for k in range(1, n_bins):
        position = k * len(present) // n_bins
        cut = present[position]
        # A cut at the smallest value would leave an empty bin below it, so it is skipped.
        if cut > present[0] and (not cuts or cut > cuts[-1]):
            cuts.append(cut)
    return tuple(cuts)


def bin_index(value: Optional[float], cuts: Sequence[float]) -> Optional[int]:
    """Index of the bin for value: 0 is below the first cut, len(cuts) is at or above the last.

    Returns None for a missing value, which has its own bin in the table.
    """
    if value is None:
        return None
    return bisect_right(cuts, value)


def build_woe_table(
    values: Sequence[Optional[float]],
    labels: Sequence[int],
    cuts: Sequence[float],
) -> WoeTable:
    """Count good and bad banks per bin, then compute WoE and IV.

    Bins: one per gap between cuts, plus one for missing values (always last).
    """
    if len(values) != len(labels):
        raise ValueError("values and labels must be the same length")
    total_bins = len(cuts) + 2  # value bins + missing bin
    good = [0] * total_bins
    bad = [0] * total_bins
    for value, label in zip(values, labels):
        index = bin_index(value, cuts)
        slot = total_bins - 1 if index is None else index
        if label == 1:
            bad[slot] += 1
        elif label == 0:
            good[slot] += 1
        else:
            raise ValueError(f"labels must be 0 or 1, got {label}")

    total_good = sum(good)
    total_bad = sum(bad)
    if total_good == 0 or total_bad == 0:
        raise ValueError("need at least one good and one bad bank to compute WoE")

    bins: list[WoeBin] = []
    information_value = 0.0
    for slot in range(total_bins):
        good_share = (good[slot] + SMOOTHING) / (total_good + SMOOTHING * total_bins)
        bad_share = (bad[slot] + SMOOTHING) / (total_bad + SMOOTHING * total_bins)
        woe = math.log(good_share / bad_share)
        information_value += (good_share - bad_share) * woe
        if slot == total_bins - 1:
            label = MISSING_LABEL
        elif not cuts:
            label = "all non-missing values"
        elif slot == 0:
            label = f"< {cuts[0]:g}"
        elif slot == len(cuts):
            label = f">= {cuts[-1]:g}"
        else:
            label = f"{cuts[slot - 1]:g} to < {cuts[slot]:g}"
        bins.append(WoeBin(label=label, good=good[slot], bad=bad[slot], woe=woe))

    return WoeTable(cuts=tuple(cuts), bins=tuple(bins), information_value=information_value)
