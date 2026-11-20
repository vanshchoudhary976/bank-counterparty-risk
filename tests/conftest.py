from __future__ import annotations

from pathlib import Path

import pytest

from credit_risk.config import (
    FDIC_FAILURE_FIELDS,
    FDIC_FINANCIAL_FIELDS,
    FDIC_INSTITUTION_FIELDS,
)
from credit_risk.warehouse import Warehouse
from tests.sample_data import FAILURES, FINANCIALS, INSTITUTIONS

REPO_ROOT = Path(__file__).resolve().parents[1]
SQL_DIR = REPO_ROOT / "sql"


@pytest.fixture
def warehouse():
    """An empty in-memory warehouse with the typed schema applied."""
    wh = Warehouse()
    wh.apply_sql_file(SQL_DIR / "01_schema.sql")
    yield wh
    wh.close()


@pytest.fixture
def loaded_warehouse(warehouse):
    """Warehouse with synthetic staging data loaded and typed tables built."""
    warehouse.load_staging("institutions", INSTITUTIONS, list(FDIC_INSTITUTION_FIELDS))
    warehouse.load_staging("financials", FINANCIALS, list(FDIC_FINANCIAL_FIELDS))
    warehouse.load_staging("failures", FAILURES, list(FDIC_FAILURE_FIELDS))
    warehouse.build_typed_tables(SQL_DIR / "02_load_fdic.sql")
    return warehouse
