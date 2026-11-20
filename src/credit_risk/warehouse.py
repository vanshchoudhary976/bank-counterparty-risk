"""DuckDB warehouse: schema, staging loads and typed-table builds.

Load order: Python writes raw API values into stg_* tables as text, then SQL in
sql/02_load_fdic.sql casts them into typed tables. Nothing is cast in Python, so
every conversion is visible in one SQL file.
"""

from __future__ import annotations

import re
from pathlib import Path

import duckdb

_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def validate_identifier(name: str) -> str:
    """Allow only plain identifiers, because table and column names are interpolated into SQL."""
    if not _IDENTIFIER.fullmatch(name):
        raise ValueError(f"Unsafe SQL identifier: {name!r}")
    return name


class Warehouse:
    def __init__(self, path: str | Path = ":memory:") -> None:
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.con = duckdb.connect(str(path))

    def close(self) -> None:
        self.con.close()

    def apply_sql_file(self, path: Path) -> None:
        self.con.execute(Path(path).read_text(encoding="utf-8"))

    def build_typed_tables(self, sql_path: Path) -> None:
        """Run the casting script. It is idempotent: it empties and refills each typed table."""
        self.apply_sql_file(sql_path)

    def load_staging(self, name: str, records: list[dict], columns: list[str]) -> int:
        """Store raw records in stg_<name> as VARCHAR. Missing values stay NULL."""
        table = f"stg_{validate_identifier(name)}"
        cols = [validate_identifier(column) for column in columns]
        column_sql = ", ".join(f'"{column}" VARCHAR' for column in cols)
        self.con.execute(f"CREATE OR REPLACE TABLE {table} ({column_sql})")
        rows = [[None if record.get(c) is None else str(record[c]) for c in cols] for record in records]
        if rows:
            placeholders = ", ".join("?" for _ in cols)
            self.con.executemany(f"INSERT INTO {table} VALUES ({placeholders})", rows)
        return len(rows)

    def record_load(self, table_name: str, source_file: str, sha256: str, source_total: int, rows_staged: int) -> None:
        self.con.execute(
            "INSERT INTO load_log (table_name, source_file, source_sha256, source_total, rows_staged) "
            "VALUES (?, ?, ?, ?, ?)",
            [table_name, source_file, sha256, source_total, rows_staged],
        )

    def count(self, table: str) -> int:
        return self.con.execute(f"SELECT COUNT(*) FROM {validate_identifier(table)}").fetchone()[0]

    def load_sec_facts(self, cik: int, rows: list[dict]) -> int:
        """Replace all facts for one company in a single transaction, so reloads never double count."""
        insert_sql = "INSERT INTO sec_facts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        self.con.execute("BEGIN TRANSACTION")
        try:
            self.con.execute("DELETE FROM sec_facts WHERE cik = ?", [cik])
            if rows:  # DuckDB's executemany rejects an empty parameter list
                self.con.executemany(
                    insert_sql,
                    [
                        (
                            cik,
                            row["taxonomy"],
                            row["concept"],
                            row["unit"],
                            row["period_end"],
                            row["val"],
                            row["fiscal_year"],
                            row["fiscal_period"],
                            row["form"],
                            row["filed"],
                            row["accession"],
                        )
                        for row in rows
                    ],
                )
            self.con.execute("COMMIT")
        except Exception:
            self.con.execute("ROLLBACK")
            raise
        return len(rows)
