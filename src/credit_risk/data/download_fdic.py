"""Download FDIC BankFind data into raw JSON files.

Run from the repository root:

    python -m credit_risk.data.download_fdic institutions
    python -m credit_risk.data.download_fdic financials
    python -m credit_risk.data.download_fdic failures

Each run writes one new file to data/raw/fdic/ and one line to its manifest.
Response pages are stored as the API returned them. The wrapper around them records
the request settings, the API-reported total and the request time.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from datetime import datetime, timezone
from typing import Any

import requests

from credit_risk.config import (
    FDIC_BASE_URL,
    FDIC_FAILURE_FIELDS,
    FDIC_FINANCIAL_FIELDS,
    FDIC_INSTITUTION_FIELDS,
    ProjectPaths,
)
from credit_risk.data.raw_store import RawStore

ENDPOINT_FIELDS: dict[str, tuple[str, ...]] = {
    "institutions": FDIC_INSTITUTION_FIELDS,
    "financials": FDIC_FINANCIAL_FIELDS,
    "failures": FDIC_FAILURE_FIELDS,
}
_FIELD_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


class FdicClient:
    """Pages through one BankFind endpoint until every row the API reports has been received."""

    def __init__(
        self,
        session: Any = None,
        base_url: str = FDIC_BASE_URL,
        page_size: int = 10000,
        pause_seconds: float = 0.2,
    ) -> None:
        if page_size < 1:
            raise ValueError("page_size must be at least 1")
        self.session = session if session is not None else requests.Session()
        self.base_url = base_url.rstrip("/")
        self.page_size = page_size
        self.pause_seconds = pause_seconds

    def fetch_pages(self, endpoint: str, fields: tuple[str, ...] | list[str], filters: str | None = None) -> list[dict]:
        """Return the parsed body of every page. Raises if the row count does not match the API total."""
        for field in fields:
            if not _FIELD_PATTERN.fullmatch(field):
                raise ValueError(f"Invalid field name: {field!r}")
        pages: list[dict] = []
        collected = 0
        offset = 0
        total: int | None = None
        while True:
            params: dict[str, Any] = {
                "format": "json",
                "limit": self.page_size,
                "offset": offset,
                "fields": ",".join(fields),
            }
            if filters:
                params["filters"] = filters
            response = self.session.get(f"{self.base_url}/{endpoint}", params=params, timeout=60)
            response.raise_for_status()
            body = response.json()
            pages.append(body)
            total = int(body["meta"]["total"])
            page_rows = body.get("data", [])
            collected += len(page_rows)
            offset += len(page_rows)
            if not page_rows or collected >= total:
                break
            time.sleep(self.pause_seconds)
        if collected != total:
            raise RuntimeError(f"{endpoint}: received {collected} rows but the API reported {total}")
        return pages


def rows_from_pages(pages: list[dict]) -> list[dict]:
    """Flatten stored pages into plain records. Each API row wraps its values under a 'data' key."""
    return [item.get("data", item) for page in pages for item in page.get("data", [])]


def download_endpoint(
    client: FdicClient,
    store: RawStore,
    endpoint: str,
    fields: list[str] | None = None,
    filters: str | None = None,
    now: datetime | None = None,
):
    if endpoint not in ENDPOINT_FIELDS:
        raise ValueError(f"Unknown endpoint {endpoint!r}. Choose from {sorted(ENDPOINT_FIELDS)}")
    chosen = tuple(fields) if fields else ENDPOINT_FIELDS[endpoint]
    requested_at = now or datetime.now(timezone.utc)
    pages = client.fetch_pages(endpoint, chosen, filters)
    payload = {
        "endpoint": endpoint,
        "fields": list(chosen),
        "filters": filters,
        "requested_at": requested_at.isoformat(),
        "total": int(pages[-1]["meta"]["total"]),
        "pages": pages,
    }
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return store.save(
        f"fdic_{endpoint}",
        body,
        source_url=f"{client.base_url}/{endpoint}",
        now=requested_at,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Download FDIC BankFind data as raw JSON.")
    parser.add_argument("endpoint", choices=sorted(ENDPOINT_FIELDS))
    parser.add_argument(
        "--fields",
        help="Comma-separated API field names. Defaults to the provisional list in config.py.",
    )
    parser.add_argument("--filters", help="Optional BankFind filter string. Check the API docs for the syntax.")
    args = parser.parse_args(argv)
    paths = ProjectPaths.default()
    fields = args.fields.split(",") if args.fields else None
    path = download_endpoint(
        FdicClient(),
        RawStore(paths.fdic_raw_dir),
        args.endpoint,
        fields=fields,
        filters=args.filters,
    )
    print(f"Saved {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
