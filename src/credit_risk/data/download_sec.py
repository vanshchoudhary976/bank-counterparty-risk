"""Download SEC EDGAR company facts (XBRL) into raw JSON files.

EDGAR requires a User-Agent with a contact email and allows at most 10 requests per second.

    export SEC_USER_AGENT="Your Name you@example.com"
    python -m credit_risk.data.download_sec <cik> [<cik> ...]

The file is saved byte for byte as EDGAR returned it.
"""

from __future__ import annotations

import argparse
import time
from datetime import datetime
from typing import Any

import requests

from credit_risk.config import SEC_COMPANYFACTS_URL, ProjectPaths, sec_user_agent
from credit_risk.data.raw_store import RawStore


class SecClient:
    """Fetches company facts for one CIK at a time, pausing to stay under the SEC rate limit."""

    def __init__(self, user_agent: str, session: Any = None, pause_seconds: float = 0.11) -> None:
        if "@" not in user_agent:
            raise ValueError("SEC requires a User-Agent that includes a contact email")
        self.user_agent = user_agent
        self.session = session if session is not None else requests.Session()
        self.pause_seconds = pause_seconds

    def fetch_companyfacts(self, cik: int) -> bytes:
        url = SEC_COMPANYFACTS_URL.format(cik=cik)
        response = self.session.get(url, headers={"User-Agent": self.user_agent}, timeout=60)
        response.raise_for_status()
        time.sleep(self.pause_seconds)
        return response.content

    @staticmethod
    def flatten_companyfacts(payload: dict) -> list[dict]:
        """Turn the nested facts -> taxonomy -> concept -> unit -> entries structure into one row per fact."""
        rows: list[dict] = []
        for taxonomy, concepts in payload.get("facts", {}).items():
            for concept, detail in concepts.items():
                for unit, entries in detail.get("units", {}).items():
                    for entry in entries:
                        rows.append(
                            {
                                "taxonomy": taxonomy,
                                "concept": concept,
                                "unit": unit,
                                "period_end": entry.get("end"),
                                "val": entry.get("val"),
                                "fiscal_year": entry.get("fy"),
                                "fiscal_period": entry.get("fp"),
                                "form": entry.get("form"),
                                "filed": entry.get("filed"),
                                "accession": entry.get("accn"),
                            }
                        )
        return rows


def save_companyfacts(client: SecClient, store: RawStore, cik: int, now: datetime | None = None):
    body = client.fetch_companyfacts(cik)
    return store.save(
        f"sec_companyfacts_cik{cik:010d}",
        body,
        source_url=SEC_COMPANYFACTS_URL.format(cik=cik),
        now=now,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Download SEC company facts as raw JSON.")
    parser.add_argument("ciks", nargs="+", type=int, help="One or more SEC CIK numbers")
    args = parser.parse_args(argv)
    paths = ProjectPaths.default()
    client = SecClient(sec_user_agent())
    store = RawStore(paths.sec_raw_dir)
    for cik in args.ciks:
        print(f"Saved {save_companyfacts(client, store, cik)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
