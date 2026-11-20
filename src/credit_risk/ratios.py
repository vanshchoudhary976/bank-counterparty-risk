"""Module A: bank ratios from FDIC call report fields.

Assumptions, recorded in docs/data_dictionary.md:
- Amounts are USD thousands. Ratios are unit-free, so they do not depend on the unit,
  but the unit matters for any absolute figure shown in a report.
- NETINC is a calendar year-to-date figure (Call Report Schedule RI: "reported on a calendar
  year-to-date basis"). A June report covers six months, a December report covers twelve.
- Annualised ROA = year-to-date ROA x (12 / months in the year-to-date period).

A ratio is None (not zero, not a guess) when an input is missing or the denominator is zero.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

MONTHS_PER_YEAR = 12


def safe_divide(numerator: Optional[float], denominator: Optional[float]) -> Optional[float]:
    """Return numerator / denominator, or None if either input is missing or the denominator is zero."""
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def equity_to_assets(total_equity: Optional[float], total_assets: Optional[float]) -> Optional[float]:
    """Capital share of the balance sheet. Higher means more loss-absorbing capital."""
    return safe_divide(total_equity, total_assets)


def loans_to_deposits(net_loans: Optional[float], total_deposits: Optional[float]) -> Optional[float]:
    """Net loans funded by deposits. Above 1 means the bank lends more than it takes in as deposits."""
    return safe_divide(net_loans, total_deposits)


def roa_ytd(net_income: Optional[float], total_assets: Optional[float]) -> Optional[float]:
    """Year-to-date net income divided by total assets at the report date.

    This is NOT an annual rate unless the report is for December. Use roa_annualised for that.
    """
    return safe_divide(net_income, total_assets)


def months_in_period(report_date: date) -> int:
    """Months covered by a calendar year-to-date income statement ending on report_date."""
    return report_date.month


def roa_annualised(net_income: Optional[float], total_assets: Optional[float], months: int) -> Optional[float]:
    """Year-to-date ROA scaled to a full year: multiply by 12 / months.

    Example: June (months = 6) doubles the six-month figure; December (months = 12) leaves it as is.
    """
    if not 1 <= months <= MONTHS_PER_YEAR:
        raise ValueError(f"months must be between 1 and 12, got {months}")
    ytd = roa_ytd(net_income, total_assets)
    return None if ytd is None else ytd * MONTHS_PER_YEAR / months


@dataclass(frozen=True)
class BankRatios:
    cert: int
    report_date: date
    equity_to_assets: Optional[float]
    loans_to_deposits: Optional[float]
    roa_ytd: Optional[float]
    roa_annualised: Optional[float]


def ratios_for_row(
    cert: int,
    report_date: date,
    total_assets: Optional[float],
    total_equity: Optional[float],
    net_loans: Optional[float],
    total_deposits: Optional[float],
    net_income: Optional[float],
) -> BankRatios:
    """Compute every Module A ratio for one bank and one report date."""
    return BankRatios(
        cert=cert,
        report_date=report_date,
        equity_to_assets=equity_to_assets(total_equity, total_assets),
        loans_to_deposits=loans_to_deposits(net_loans, total_deposits),
        roa_ytd=roa_ytd(net_income, total_assets),
        roa_annualised=roa_annualised(net_income, total_assets, months_in_period(report_date)),
    )
