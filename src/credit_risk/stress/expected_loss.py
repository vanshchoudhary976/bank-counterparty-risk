"""Module D step 3: expected loss and exposure change under stress. All illustrative.

Expected loss is EAD x PD x LGD, the same definition as Module C. Under a stress scenario two things can change:
the grade, and therefore the PD, and the exposure. The exposure changes only for counterparties with a repo trade
that are downgraded by at least DOWNGRADE_GRADES. For those, the Module C wrong-way factor is applied to the base EAD.
Every number here is an assumption carried over from Module C, not a regulatory or IFRS 9 output.
"""

from __future__ import annotations

from dataclasses import dataclass

from credit_risk.exposure.measures import DOWNGRADE_GRADES, LGD_BASE, WRONG_WAY_FACTOR, pd_for_grade


@dataclass(frozen=True)
class StressRow:
    cert: int
    name: str
    scenario: str
    base_grade: int
    stressed_grade: int
    base_pd: float
    stressed_pd: float
    base_ead: float
    stressed_ead: float
    base_el: float
    stressed_el: float

    @property
    def el_change(self) -> float:
        return self.stressed_el - self.base_el


def validate_grade(grade: int) -> int:
    if not 1 <= grade <= 10:
        raise ValueError(f"grade must be 1 to 10, got {grade}")
    return grade


def grade_downgrade(base_grade: int, stressed_grade: int) -> int:
    """Number of grades the counterparty moves towards the worst grade (10). Negative means an upgrade."""
    return validate_grade(stressed_grade) - validate_grade(base_grade)


def expected_loss(ead: float, pd: float, lgd: float = LGD_BASE) -> float:
    if ead < 0:
        raise ValueError(f"ead must not be negative, got {ead}")
    if not 0.0 <= pd <= 1.0:
        raise ValueError(f"pd must be between 0 and 1, got {pd}")
    if not 0.0 <= lgd <= 1.0:
        raise ValueError(f"lgd must be between 0 and 1, got {lgd}")
    return ead * pd * lgd


def stressed_ead(base_ead: float, base_grade: int, stressed_grade: int, has_repo: bool) -> float:
    """Exposure under stress. Only repo counterparties downgraded by at least DOWNGRADE_GRADES are scaled."""
    if base_ead < 0:
        raise ValueError(f"base_ead must not be negative, got {base_ead}")
    if has_repo and grade_downgrade(base_grade, stressed_grade) >= DOWNGRADE_GRADES:
        return base_ead * WRONG_WAY_FACTOR
    return base_ead


def build_row(
    cert: int, name: str, scenario: str, base_grade: int, stressed_grade: int, base_ead: float, has_repo: bool
) -> StressRow:
    base_pd = pd_for_grade(validate_grade(base_grade))
    stressed_pd = pd_for_grade(validate_grade(stressed_grade))
    s_ead = stressed_ead(base_ead, base_grade, stressed_grade, has_repo)
    return StressRow(
        cert=cert,
        name=name,
        scenario=scenario,
        base_grade=base_grade,
        stressed_grade=stressed_grade,
        base_pd=base_pd,
        stressed_pd=stressed_pd,
        base_ead=base_ead,
        stressed_ead=s_ead,
        base_el=expected_loss(base_ead, base_pd),
        stressed_el=expected_loss(s_ead, stressed_pd),
    )


def scenario_totals(rows: list[StressRow]) -> dict[str, tuple[float, float, float]]:
    """Scenario name -> (base expected loss total, stressed total, change), summed over counterparties."""
    totals: dict[str, tuple[float, float, float]] = {}
    for r in rows:
        base, stressed, change = totals.get(r.scenario, (0.0, 0.0, 0.0))
        totals[r.scenario] = (base + r.base_el, stressed + r.stressed_el, change + r.el_change)
    return totals


def format_expected_loss(rows: list[StressRow]) -> str:
    lines = [
        "ILLUSTRATIVE. Expected loss = EAD x PD x LGD at LGD "
        f"{LGD_BASE:.0%} (base case). PDs come from the validation grade table with a floor.",
        f"Repo exposure is scaled by {WRONG_WAY_FACTOR} only when a repo counterparty is downgraded by "
        f"{DOWNGRADE_GRADES} or more grades. Stressed exposure for other counterparties is unchanged.",
        "",
    ]
    current = None
    for r in rows:
        if r.scenario != current:
            if current is not None:
                lines.append("")
            current = r.scenario
            lines.append(f"{r.scenario}")
        lines.append(
            f"  {r.name} (cert {r.cert}): grade {r.base_grade} to {r.stressed_grade}, "
            f"PD {r.base_pd:.4%} to {r.stressed_pd:.4%}, "
            f"EAD {r.base_ead:,.0f} to {r.stressed_ead:,.0f}, "
            f"EL {r.base_el:,.0f} to {r.stressed_el:,.0f} (change {r.el_change:+,.0f})"
        )
    lines.append("")
    lines.append("Totals by scenario:")
    for scenario, (base, stressed, change) in scenario_totals(rows).items():
        lines.append(
            f"  {scenario}: base EL {base:,.0f}, stressed EL {stressed:,.0f}, change {change:+,.0f}"
        )
    return "\n".join(lines) + "\n"
