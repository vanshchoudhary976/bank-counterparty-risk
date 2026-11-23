"""Module D step 4: export the expected loss stress rows to CSV for the Tableau dashboard. ILLUSTRATIVE.

One row per counterparty and scenario. The label column repeats ILLUSTRATIVE on every row, so the label
travels with the data into the dashboard.
"""

from __future__ import annotations

import csv
from dataclasses import asdict
from pathlib import Path

from credit_risk.stress.expected_loss import StressRow

LABEL = "ILLUSTRATIVE"
CSV_FIELDS = (
    "label",
    "cert",
    "name",
    "scenario",
    "base_grade",
    "stressed_grade",
    "base_pd",
    "stressed_pd",
    "base_ead",
    "stressed_ead",
    "base_el",
    "stressed_el",
    "el_change",
)


def row_to_record(row: StressRow) -> dict:
    record = asdict(row)
    record["label"] = LABEL
    record["el_change"] = row.el_change
    return {field: record[field] for field in CSV_FIELDS}


def write_csv(rows: list[StressRow], path: Path) -> int:
    """Write the rows with a header line. Returns the number of data rows written."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row_to_record(row))
    return len(rows)
