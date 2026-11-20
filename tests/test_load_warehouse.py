import json
import shutil
from datetime import datetime, timezone

import duckdb
import pytest

from credit_risk.config import (
    FDIC_FAILURE_FIELDS,
    FDIC_FINANCIAL_FIELDS,
    FDIC_INSTITUTION_FIELDS,
    ProjectPaths,
)
from credit_risk.data.load_warehouse import load_all, read_fdic_source
from credit_risk.data.raw_store import RawStore
from tests.conftest import REPO_ROOT
from tests.sample_data import FAILURES, FINANCIALS, INSTITUTIONS, fdic_page

T0 = datetime(2026, 11, 19, 12, 0, 0, tzinfo=timezone.utc)
T1 = datetime(2026, 11, 19, 12, 1, 0, tzinfo=timezone.utc)


def _save_fdic(store, endpoint, fields, rows, now, total=None):
    payload = {
        "endpoint": endpoint,
        "fields": list(fields),
        "filters": None,
        "requested_at": now.isoformat(),
        "total": len(rows) if total is None else total,
        "pages": [fdic_page(rows, total=total)],
    }
    return store.save(f"fdic_{endpoint}", json.dumps(payload).encode("utf-8"), source_url="test", now=now)


@pytest.fixture
def project(tmp_path):
    """A throwaway project root with a copy of the SQL folder and synthetic raw files."""
    shutil.copytree(REPO_ROOT / "sql", tmp_path / "sql")
    paths = ProjectPaths(root=tmp_path)
    store = RawStore(paths.fdic_raw_dir)
    _save_fdic(store, "institutions", FDIC_INSTITUTION_FIELDS, INSTITUTIONS, T0)
    _save_fdic(store, "financials", FDIC_FINANCIAL_FIELDS, FINANCIALS, T0)
    _save_fdic(store, "failures", FDIC_FAILURE_FIELDS, FAILURES, T0)
    return paths


def test_read_fdic_source_rejects_tampered_file(project):
    store = RawStore(project.fdic_raw_dir)
    path = store.latest("fdic_financials")
    path.write_bytes(path.read_bytes().replace(b"1000000", b"9999999"))
    with pytest.raises(ValueError, match="checksum"):
        read_fdic_source(store, "financials")


def test_read_fdic_source_rejects_row_count_mismatch(tmp_path):
    store = RawStore(tmp_path)
    _save_fdic(store, "institutions", FDIC_INSTITUTION_FIELDS, INSTITUTIONS[:2], T0, total=5)
    with pytest.raises(ValueError, match="holds 2 rows but the API total was 5"):
        read_fdic_source(store, "institutions")


def test_read_fdic_source_reports_missing_download(tmp_path):
    with pytest.raises(FileNotFoundError, match="download_fdic"):
        read_fdic_source(RawStore(tmp_path), "failures")


def test_load_all_passes_every_check_on_synthetic_data(project, tmp_path):
    results = load_all(project, db_path=tmp_path / "test.duckdb")
    failed = [result.name for result in results if not result.passed]
    assert failed == []
    assert len(results) >= 10


def test_load_all_includes_sec_check_when_sec_files_exist(project, tmp_path):
    sec_store = RawStore(project.sec_raw_dir)
    facts = {
        "facts": {
            "dei": {
                "EntityName": {
                    "units": {
                        "pure": [
                            {"end": "2023-12-31", "val": 0, "accn": "x", "fy": 2023, "fp": "FY",
                             "form": "10-K", "filed": "2024-02-01"}
                        ]
                    }
                }
            }
        }
    }
    sec_store.save("sec_companyfacts_cik0000320193", json.dumps(facts).encode("utf-8"), source_url="test", now=T0)
    results = load_all(project, db_path=tmp_path / "test.duckdb")
    sec_results = [result for result in results if "SEC" in result.name]
    assert len(sec_results) == 1
    assert sec_results[0].passed is True


def test_load_all_fails_loudly_on_bad_report_date(project, tmp_path):
    bad_rows = [dict(FINANCIALS[0], REPDTE="2023-03-31")]
    _save_fdic(RawStore(project.fdic_raw_dir), "financials", FDIC_FINANCIAL_FIELDS, bad_rows, T1)
    with pytest.raises(duckdb.Error):
        load_all(project, db_path=tmp_path / "test.duckdb")
