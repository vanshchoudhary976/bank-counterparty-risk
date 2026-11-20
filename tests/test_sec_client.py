from datetime import datetime, timezone

import pytest

from credit_risk.data.download_sec import SecClient, save_companyfacts
from credit_risk.data.raw_store import RawStore
from tests.fakes import FakeResponse, FakeSession

NOW = datetime(2026, 11, 19, 12, 0, 0, tzinfo=timezone.utc)
AGENT = "Vansh Choudhary vansh@example.com"


def test_client_requires_contact_email_in_user_agent():
    with pytest.raises(ValueError, match="contact email"):
        SecClient("Vansh Choudhary", session=FakeSession([]))


def test_fetch_uses_zero_padded_cik_and_user_agent():
    raw = b'{"cik": 320193, "facts": {}}'
    session = FakeSession([FakeResponse(content=raw)])
    client = SecClient(AGENT, session=session, pause_seconds=0)
    body = client.fetch_companyfacts(320193)
    assert session.calls[0]["url"].endswith("/CIK0000320193.json")
    assert session.calls[0]["headers"]["User-Agent"] == AGENT
    assert body == raw


def test_flatten_returns_one_row_per_fact():
    payload = {
        "facts": {
            "us-gaap": {
                "Revenues": {
                    "units": {
                        "USD": [
                            {
                                "end": "2023-12-31",
                                "val": 100,
                                "accn": "0001-24-000001",
                                "fy": 2023,
                                "fp": "FY",
                                "form": "10-K",
                                "filed": "2024-02-01",
                            }
                        ]
                    }
                }
            }
        }
    }
    rows = SecClient.flatten_companyfacts(payload)
    assert len(rows) == 1
    assert rows[0]["concept"] == "Revenues"
    assert rows[0]["unit"] == "USD"
    assert rows[0]["period_end"] == "2023-12-31"
    assert rows[0]["val"] == 100
    assert rows[0]["accession"] == "0001-24-000001"


def test_flatten_handles_empty_facts():
    assert SecClient.flatten_companyfacts({"facts": {}}) == []
    assert SecClient.flatten_companyfacts({}) == []


def test_save_companyfacts_keeps_bytes_exactly(tmp_path):
    raw = b'{"facts": {"dei": {}}}   \n'
    session = FakeSession([FakeResponse(content=raw)])
    client = SecClient(AGENT, session=session, pause_seconds=0)
    store = RawStore(tmp_path)
    path = save_companyfacts(client, store, 320193, now=NOW)
    assert path.name == "sec_companyfacts_cik0000320193_20261119T120000Z.json"
    assert path.read_bytes() == raw
    assert store.verify(path)
