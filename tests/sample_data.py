"""Synthetic test fixture. Bank names and certificate numbers are invented, except that the three
2023 failure names are included so the known-failure check has something to find.
Nothing here is real financial data."""

from __future__ import annotations

INSTITUTIONS: list[dict] = [
    {"CERT": "1001", "NAME": "ALPHA NATIONAL BANK", "STALP": "CA", "ACTIVE": "1"},
    {"CERT": "1002", "NAME": "BETA COMMUNITY BANK", "STALP": "NY", "ACTIVE": "1"},
    {"CERT": "1003", "NAME": "SILICON VALLEY BANK", "STALP": "CA", "ACTIVE": "0"},
    {"CERT": "1004", "NAME": "SIGNATURE BANK", "STALP": "NY", "ACTIVE": "0"},
    {"CERT": "1005", "NAME": "FIRST REPUBLIC BANK", "STALP": "CA", "ACTIVE": "0"},
]

FINANCIALS: list[dict] = [
    {"CERT": "1001", "REPDTE": "20230331", "ASSET": "1000000", "EQTOT": "90000", "LNLSNET": "600000", "DEP": "800000", "NETINC": "2000", "RBC1AAJ": "9.5", "LNLSRES": "6000", "EEFFR": "60.0"},
    {"CERT": "1001", "REPDTE": "20230630", "ASSET": "1010000", "EQTOT": "91000", "LNLSNET": "605000", "DEP": "805000", "NETINC": "2100", "RBC1AAJ": "9.5", "LNLSRES": "6000", "EEFFR": "60.0"},
    {"CERT": "1001", "REPDTE": "20231231", "ASSET": "1050000", "EQTOT": "95000", "LNLSNET": "620000", "DEP": "820000", "NETINC": "2300", "RBC1AAJ": "9.5", "LNLSRES": "6000", "EEFFR": "60.0"},
    {"CERT": "1002", "REPDTE": "20231231", "ASSET": "500000", "EQTOT": "45000", "LNLSNET": "300000", "DEP": "420000", "NETINC": "900", "RBC1AAJ": "9.5", "LNLSRES": "6000", "EEFFR": "60.0"},
    {"CERT": "1003", "REPDTE": "20221231", "ASSET": "210000", "EQTOT": "16000", "LNLSNET": "70000", "DEP": "175000", "NETINC": "1200", "RBC1AAJ": "9.5", "LNLSRES": "6000", "EEFFR": "60.0"},
    {"CERT": "1005", "REPDTE": "20221231", "ASSET": "200000", "EQTOT": "10000", "LNLSNET": "120000", "DEP": "165000", "NETINC": "800", "RBC1AAJ": "9.5", "LNLSRES": "6000", "EEFFR": "60.0"},
]

FAILURES: list[dict] = [
    {"CERT": "1003", "NAME": "SILICON VALLEY BANK", "FAILDATE": "2023-03-10"},
    {"CERT": "1004", "NAME": "SIGNATURE BANK", "FAILDATE": "2023-03-12"},
    {"CERT": "1005", "NAME": "FIRST REPUBLIC BANK", "FAILDATE": "2023-05-01"},
]

SOURCE_TOTALS: dict[str, int] = {
    "institutions": len(INSTITUTIONS),
    "financials": len(FINANCIALS),
    "failures": len(FAILURES),
}


def fdic_page(rows: list[dict], total: int | None = None) -> dict:
    """One page as the BankFind API returns it: each row wrapped under a 'data' key."""
    return {"meta": {"total": len(rows) if total is None else total}, "data": [{"data": row} for row in rows]}
