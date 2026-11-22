"""Load the newest raw files into DuckDB, build typed tables and run the data checks.

    python -m credit_risk.data.load_warehouse

Exits with status 1 if any check fails, so a bad load cannot pass silently.
Every raw file is verified against its manifest checksum before it is read.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

from credit_risk.checks import CheckResult, DataChecks
from credit_risk.config import ProjectPaths
from credit_risk.data.download_fdic import rows_from_pages
from credit_risk.data.download_sec import SecClient
from credit_risk.data.raw_store import RawStore
from credit_risk.warehouse import Warehouse

FDIC_ENDPOINTS: tuple[str, ...] = ("institutions", "financials", "failures")
_SEC_FILE = re.compile(r"sec_companyfacts_cik(\d{10})_")


@dataclass(frozen=True)
class FdicSource:
    endpoint: str
    file: Path
    sha256: str
    total: int
    fields: list[str]
    records: list[dict]


def read_fdic_source(store: RawStore, endpoint: str) -> FdicSource:
    path = store.latest(f"fdic_{endpoint}")
    if path is None:
        raise FileNotFoundError(f"No raw file for fdic_{endpoint}. Run download_fdic first.")
    if not store.verify(path):
        raise ValueError(f"{path.name} does not match its manifest checksum. Re-download it.")
    raw = path.read_bytes()
    payload = json.loads(raw)
    records = rows_from_pages(payload["pages"])
    total = int(payload["total"])
    if len(records) != total:
        raise ValueError(f"{path.name} holds {len(records)} rows but the API total was {total}")
    return FdicSource(
        endpoint=endpoint,
        file=path,
        sha256=hashlib.sha256(raw).hexdigest(),
        total=total,
        fields=list(payload["fields"]),
        records=records,
    )


def load_sec(warehouse: Warehouse, store: RawStore) -> list[int]:
    """Load the newest company-facts file for every CIK in the SEC manifest. Returns the CIKs loaded."""
    ciks = sorted({int(match.group(1)) for entry in store.entries() if (match := _SEC_FILE.match(entry["file"]))})
    for cik in ciks:
        path = store.latest(f"sec_companyfacts_cik{cik:010d}")
        if path is None or not store.verify(path):
            raise ValueError(f"SEC file for CIK {cik} is missing or fails its checksum")
        rows = SecClient.flatten_companyfacts(json.loads(path.read_bytes()))
        warehouse.load_sec_facts(cik, rows)
    return ciks


def load_all(paths: ProjectPaths, db_path: Path | None = None) -> list[CheckResult]:
    fdic_store = RawStore(paths.fdic_raw_dir)
    sec_store = RawStore(paths.sec_raw_dir)
    warehouse = Warehouse(db_path if db_path is not None else paths.warehouse_file)
    try:
        warehouse.apply_sql_file(paths.sql_dir / "01_schema.sql")
        totals: dict[str, int] = {}
        for endpoint in FDIC_ENDPOINTS:
            source = read_fdic_source(fdic_store, endpoint)
            staged = warehouse.load_staging(endpoint, source.records, source.fields)
            warehouse.record_load(f"stg_{endpoint}", source.file.name, source.sha256, source.total, staged)
            totals[endpoint] = source.total
        warehouse.build_typed_tables(paths.sql_dir / "02_load_fdic.sql")
        warehouse.apply_sql_file(paths.sql_dir / "03_ratios.sql")
        warehouse.apply_sql_file(paths.sql_dir / "04_scorecard_inputs.sql")
        sec_ciks = load_sec(warehouse, sec_store)
        return DataChecks(warehouse.con).run_all(totals, sec_ciks=sec_ciks or None)
    finally:
        warehouse.close()


def main() -> int:
    results = load_all(ProjectPaths.default())
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"[{status}] {result.name}: {result.detail}")
    failed = [result for result in results if not result.passed]
    print(f"{len(results) - len(failed)} of {len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
