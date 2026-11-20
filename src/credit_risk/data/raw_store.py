"""Raw file storage. Files are written once, checksummed and never edited."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

MANIFEST_NAME = "manifest.jsonl"
_NAME_PATTERN = re.compile(r"[a-z0-9_]+")


class RawStore:
    """Writes raw payloads into one folder and logs each file, with its SHA-256, in a manifest.

    The checksum lets the loader prove that a file has not changed since it was downloaded.
    """

    def __init__(self, directory: Path) -> None:
        self.directory = Path(directory)

    def save(self, name: str, payload: bytes, source_url: str, now: datetime | None = None) -> Path:
        if not _NAME_PATTERN.fullmatch(name):
            raise ValueError(f"Raw file name must use lowercase letters, digits and underscores: {name!r}")
        self.directory.mkdir(parents=True, exist_ok=True)
        stamp = (now or datetime.now(timezone.utc)).strftime("%Y%m%dT%H%M%SZ")
        path = self.directory / f"{name}_{stamp}.json"
        if path.exists():
            raise FileExistsError(f"{path.name} already exists. Raw files are never overwritten.")
        path.write_bytes(payload)
        entry = {
            "file": path.name,
            "source_url": source_url,
            "sha256": hashlib.sha256(payload).hexdigest(),
            "bytes": len(payload),
            "saved_at": stamp,
        }
        with (self.directory / MANIFEST_NAME).open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry) + "\n")
        return path

    def entries(self) -> list[dict]:
        manifest = self.directory / MANIFEST_NAME
        if not manifest.exists():
            return []
        lines = manifest.read_text(encoding="utf-8").splitlines()
        return [json.loads(line) for line in lines if line.strip()]

    def latest(self, name: str) -> Path | None:
        """Return the newest file saved under this name, or None if there is none."""
        prefix = f"{name}_"
        matches = [entry for entry in self.entries() if entry["file"].startswith(prefix)]
        if not matches:
            return None
        newest = max(matches, key=lambda entry: entry["saved_at"])
        return self.directory / newest["file"]

    def verify(self, path: Path) -> bool:
        """True only if the file exists in the manifest and its bytes still match the logged SHA-256."""
        path = Path(path)
        entry = next((item for item in self.entries() if item["file"] == path.name), None)
        if entry is None or not path.exists():
            return False
        return hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"]
