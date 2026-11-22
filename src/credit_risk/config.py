"""Project paths and source settings for the Project F data layer.

Every path is derived from the repository root, so a clean clone runs the same way.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

FDIC_BASE_URL = "https://banks.data.fdic.gov/api"
SEC_COMPANYFACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"

# PROVISIONAL field names. Each one must be confirmed in docs/data_dictionary.md
# before any ratio uses it. sql/02_load_fdic.sql refers to these same names.
FDIC_INSTITUTION_FIELDS: tuple[str, ...] = ("CERT", "NAME", "STALP", "ACTIVE")
# Week 3 additions for the six-ratio scorecard: RBC1AAJ (Tier 1 leverage, percent), LNLSRES (allowance for loan
# and lease losses, $ thousands), EEFFR (efficiency ratio, percent). Units to be confirmed on raw data.
FDIC_FINANCIAL_FIELDS: tuple[str, ...] = (
    "CERT", "REPDTE", "ASSET", "EQTOT", "LNLSNET", "DEP", "NETINC", "RBC1AAJ", "LNLSRES", "EEFFR",
)
FDIC_FAILURE_FIELDS: tuple[str, ...] = ("CERT", "NAME", "FAILDATE")

_EMAIL_PATTERN = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")


@dataclass(frozen=True)
class ProjectPaths:
    """Every location the data layer reads or writes, relative to one root folder."""

    root: Path

    @classmethod
    def default(cls) -> "ProjectPaths":
        # This file is src/credit_risk/config.py, so the root is three levels up.
        return cls(root=Path(__file__).resolve().parents[2])

    @property
    def fdic_raw_dir(self) -> Path:
        return self.root / "data" / "raw" / "fdic"

    @property
    def sec_raw_dir(self) -> Path:
        return self.root / "data" / "raw" / "sec"

    @property
    def warehouse_file(self) -> Path:
        return self.root / "data" / "warehouse.duckdb"

    @property
    def sql_dir(self) -> Path:
        return self.root / "sql"


def sec_user_agent(environ: dict[str, str] | None = None) -> str:
    """Return the SEC User-Agent. EDGAR requires a name and contact email in it."""
    env = os.environ if environ is None else environ
    value = env.get("SEC_USER_AGENT", "").strip()
    if not _EMAIL_PATTERN.search(value):
        raise ValueError(
            "Set SEC_USER_AGENT to your name and email, for example: "
            'export SEC_USER_AGENT="Your Name you@example.com"'
        )
    return value
