"""Back-test of the early-warning rules on failed and surviving banks."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Mapping, Sequence

from credit_risk.warning.rules import Row, PeerThresholds, colour, evaluate

LOOKBACK_QUARTERS = 12
EARLY_QUARTERS = 4


@dataclass
class BacktestResult:
    failures: int = 0
    red_first_warning: dict[int, int] = field(default_factory=dict)  # cert -> quarters of red warning
    misses: list[tuple[int, str]] = field(default_factory=list)
    survivors: int = 0
    survivors_with_red: int = 0

    @property
    def share_flagged_early(self) -> float:
        if not self.failures:
            return 0.0
        return sum(1 for q in self.red_first_warning.values() if q >= EARLY_QUARTERS) / self.failures

    @property
    def false_alarm_rate(self) -> float:
        return self.survivors_with_red / self.survivors if self.survivors else 0.0


def _quarters_between(a: date, b: date) -> int:
    return (b.year - a.year) * 4 + (b.month - a.month) // 3


def backtest(
    rows_by_cert: Mapping[int, Sequence[Row]],
    failures: Mapping[int, date],
    window_start: date,
    window_end: date,
    peers_by_quarter: Mapping[date, PeerThresholds],
) -> BacktestResult:
    result = BacktestResult()
    for cert, rows in rows_by_cert.items():
        rows = [r for r in rows if window_start <= r.report_date <= window_end]
        if not rows:
            continue
        fail_date = failures.get(cert)
        history: list[Row] = []
        first_red = None
        first_any = None
        for r in sorted(rows, key=lambda x: x.report_date):
            if fail_date is not None and r.report_date >= fail_date:
                break
            history.append(r)
            fired = evaluate(history, peers_by_quarter[r.report_date])
            c = colour(fired)
            if c == "red" and first_red is None:
                first_red = r.report_date
            if c in ("amber", "red") and first_any is None:
                first_any = r.report_date
        if fail_date is not None and window_start <= fail_date <= window_end:
            result.failures += 1
            if first_red is not None:
                lead = _quarters_between(first_red, fail_date)
                result.red_first_warning[cert] = lead
                if lead < EARLY_QUARTERS:
                    result.misses.append((cert, f"first red warning {lead} quarters before failure"))
            else:
                reason = "no amber or red warning" if first_any is None else "amber only, never red"
                result.misses.append((cert, reason))
        elif fail_date is None or fail_date > window_end:
            result.survivors += 1
            if first_red is not None:
                result.survivors_with_red += 1
    return result
