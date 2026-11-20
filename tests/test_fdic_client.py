import json
from datetime import datetime, timezone

import pytest

from credit_risk.config import FDIC_INSTITUTION_FIELDS
from credit_risk.data.download_fdic import FdicClient, download_endpoint, rows_from_pages
from credit_risk.data.raw_store import RawStore
from tests.fakes import FakeResponse, FakeSession
from tests.sample_data import fdic_page

NOW = datetime(2026, 11, 19, 12, 0, 0, tzinfo=timezone.utc)


def test_fetch_pages_walks_offsets_until_total_is_reached():
    session = FakeSession(
        [
            FakeResponse(fdic_page([{"CERT": 1}, {"CERT": 2}], total=5)),
            FakeResponse(fdic_page([{"CERT": 3}, {"CERT": 4}], total=5)),
            FakeResponse(fdic_page([{"CERT": 5}], total=5)),
        ]
    )
    client = FdicClient(session=session, page_size=2, pause_seconds=0)
    pages = client.fetch_pages("financials", ("CERT",))
    assert [call["params"]["offset"] for call in session.calls] == [0, 2, 4]
    assert [row["CERT"] for row in rows_from_pages(pages)] == [1, 2, 3, 4, 5]


def test_fetch_pages_raises_when_api_returns_fewer_rows_than_total():
    session = FakeSession([FakeResponse(fdic_page([], total=5))])
    client = FdicClient(session=session, pause_seconds=0)
    with pytest.raises(RuntimeError, match="received 0 rows"):
        client.fetch_pages("institutions", ("CERT",))


def test_fetch_pages_rejects_unsafe_field_names_before_any_request():
    session = FakeSession([])
    client = FdicClient(session=session, pause_seconds=0)
    with pytest.raises(ValueError, match="Invalid field name"):
        client.fetch_pages("institutions", ("CERT", "NAME; DROP"))
    assert session.calls == []


def test_http_error_is_raised():
    session = FakeSession([FakeResponse({"meta": {"total": 0}, "data": []}, status=500)])
    client = FdicClient(session=session, pause_seconds=0)
    with pytest.raises(RuntimeError, match="HTTP 500"):
        client.fetch_pages("institutions", ("CERT",))


def test_fetch_pages_sends_fields_and_filters_as_parameters():
    session = FakeSession([FakeResponse(fdic_page([], total=0))])
    client = FdicClient(session=session, pause_seconds=0)
    client.fetch_pages("financials", ("CERT", "REPDTE"), filters="REPDTE:20231231")
    params = session.calls[0]["params"]
    assert params["fields"] == "CERT,REPDTE"
    assert params["filters"] == "REPDTE:20231231"
    assert params["format"] == "json"


def test_invalid_page_size_is_rejected():
    with pytest.raises(ValueError):
        FdicClient(session=FakeSession([]), page_size=0)


def test_download_endpoint_writes_one_raw_file_with_total(tmp_path):
    session = FakeSession([FakeResponse(fdic_page([{"CERT": 1001, "NAME": "A"}], total=1))])
    client = FdicClient(session=session, pause_seconds=0)
    store = RawStore(tmp_path)
    path = download_endpoint(client, store, "institutions", now=NOW)
    assert path.name == "fdic_institutions_20261119T120000Z.json"
    payload = json.loads(path.read_bytes())
    assert payload["endpoint"] == "institutions"
    assert payload["total"] == 1
    assert len(payload["pages"]) == 1
    assert store.verify(path)


def test_download_endpoint_uses_default_fields_when_none_given(tmp_path):
    session = FakeSession([FakeResponse(fdic_page([], total=0))])
    client = FdicClient(session=session, pause_seconds=0)
    download_endpoint(client, RawStore(tmp_path), "institutions", now=NOW)
    assert session.calls[0]["params"]["fields"] == ",".join(FDIC_INSTITUTION_FIELDS)


def test_download_endpoint_rejects_unknown_endpoint(tmp_path):
    client = FdicClient(session=FakeSession([]), pause_seconds=0)
    with pytest.raises(ValueError, match="Unknown endpoint"):
        download_endpoint(client, RawStore(tmp_path), "branches", now=NOW)
