from pathlib import Path

import pytest

from credit_risk.config import ProjectPaths, sec_user_agent


def test_default_root_contains_sql_folder():
    paths = ProjectPaths.default()
    assert paths.sql_dir.is_dir()
    assert (paths.sql_dir / "01_schema.sql").exists()


def test_paths_are_derived_from_root():
    paths = ProjectPaths(root=Path("/tmp/project-f"))
    assert paths.fdic_raw_dir == Path("/tmp/project-f/data/raw/fdic")
    assert paths.sec_raw_dir == Path("/tmp/project-f/data/raw/sec")
    assert paths.warehouse_file == Path("/tmp/project-f/data/warehouse.duckdb")


def test_sec_user_agent_accepts_name_and_email():
    agent = sec_user_agent({"SEC_USER_AGENT": "  Vansh Choudhary vansh@example.com  "})
    assert agent == "Vansh Choudhary vansh@example.com"


def test_sec_user_agent_rejects_missing_email():
    with pytest.raises(ValueError, match="SEC_USER_AGENT"):
        sec_user_agent({"SEC_USER_AGENT": "Vansh Choudhary"})


def test_sec_user_agent_rejects_unset_variable():
    with pytest.raises(ValueError):
        sec_user_agent({})
