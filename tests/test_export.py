"""Tests for Module D step 4: the CSV export that feeds the Tableau dashboard."""

import csv

import pytest

from credit_risk.stress.expected_loss import build_row
from credit_risk.stress.export import CSV_FIELDS, LABEL, row_to_record, write_csv


def sample_rows():
    return [
        build_row(1, "Bank A", "Credit shock", 3, 10, base_ead=1_000_000.0, has_repo=False),
        build_row(2, "Bank B", "Rate shock", 2, 4, base_ead=500_000.0, has_repo=True),
    ]


def test_record_has_every_csv_field_and_the_label():
    rec = row_to_record(sample_rows()[0])
    assert tuple(rec.keys()) == CSV_FIELDS
    assert rec["label"] == LABEL


def test_record_el_change_is_stressed_minus_base():
    row = sample_rows()[0]
    assert row_to_record(row)["el_change"] == pytest.approx(row.stressed_el - row.base_el)


def test_write_csv_writes_header_and_one_line_per_row(tmp_path):
    path = tmp_path / "tableau" / "expected_loss_stress.csv"
    count = write_csv(sample_rows(), path)
    assert count == 2
    with open(path, encoding="utf-8", newline="") as fh:
        reader = list(csv.DictReader(fh))
    assert len(reader) == 2
    assert reader[0]["name"] == "Bank A"
    assert reader[0]["scenario"] == "Credit shock"
    assert reader[0]["label"] == LABEL
    assert float(reader[0]["el_change"]) > 0


def test_write_csv_round_trips_stressed_ead(tmp_path):
    rows = sample_rows()
    path = tmp_path / "out.csv"
    write_csv(rows, path)
    with open(path, encoding="utf-8", newline="") as fh:
        second = list(csv.DictReader(fh))[1]
    assert float(second["stressed_ead"]) == pytest.approx(rows[1].stressed_ead)


def test_write_csv_with_no_rows_writes_header_only(tmp_path):
    path = tmp_path / "empty.csv"
    assert write_csv([], path) == 0
    with open(path, encoding="utf-8", newline="") as fh:
        assert fh.read().strip() == ",".join(CSV_FIELDS)
