from datetime import datetime, timezone

import pytest

from credit_risk.data.raw_store import RawStore

NOW = datetime(2026, 11, 19, 12, 0, 0, tzinfo=timezone.utc)
LATER = datetime(2026, 11, 19, 12, 5, 0, tzinfo=timezone.utc)


def test_save_writes_file_and_manifest_entry(tmp_path):
    store = RawStore(tmp_path / "fdic")
    path = store.save("fdic_failures", b'{"data":[]}', source_url="https://example.test", now=NOW)
    assert path.name == "fdic_failures_20261119T120000Z.json"
    assert path.read_bytes() == b'{"data":[]}'
    entries = store.entries()
    assert len(entries) == 1
    assert entries[0]["source_url"] == "https://example.test"
    assert entries[0]["bytes"] == len(b'{"data":[]}')


def test_verify_is_true_for_untouched_file(tmp_path):
    store = RawStore(tmp_path)
    path = store.save("fdic_institutions", b"{}", source_url="x", now=NOW)
    assert store.verify(path) is True


def test_verify_detects_tampering(tmp_path):
    store = RawStore(tmp_path)
    path = store.save("fdic_institutions", b"{}", source_url="x", now=NOW)
    path.write_bytes(b'{"edited": true}')
    assert store.verify(path) is False


def test_save_never_overwrites(tmp_path):
    store = RawStore(tmp_path)
    store.save("fdic_institutions", b"{}", source_url="x", now=NOW)
    with pytest.raises(FileExistsError):
        store.save("fdic_institutions", b"{}", source_url="x", now=NOW)


def test_latest_returns_newest_saved_file(tmp_path):
    store = RawStore(tmp_path)
    store.save("fdic_financials", b"old", source_url="x", now=NOW)
    newest = store.save("fdic_financials", b"new", source_url="x", now=LATER)
    assert store.latest("fdic_financials") == newest


def test_latest_returns_none_when_nothing_saved(tmp_path):
    assert RawStore(tmp_path).latest("fdic_financials") is None


def test_latest_does_not_confuse_similar_names(tmp_path):
    store = RawStore(tmp_path)
    store.save("fdic_failures", b"{}", source_url="x", now=NOW)
    assert store.latest("fdic_fail") is None


def test_rejects_unsafe_file_names(tmp_path):
    with pytest.raises(ValueError):
        RawStore(tmp_path).save("../escape", b"{}", source_url="x", now=NOW)


def test_verify_is_false_for_file_not_in_manifest(tmp_path):
    store = RawStore(tmp_path)
    stray = tmp_path / "stray_20261119T120000Z.json"
    stray.write_bytes(b"{}")
    assert store.verify(stray) is False
