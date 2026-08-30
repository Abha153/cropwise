"""
Direct tests of app/services/live_market_data.py -- specifically the layer
that builds the actual HTTP request and parses the actual HTTP response,
which app/tests/test_mandi_directory.py deliberately mocks OUT (it tests
the layer above this one). Neither file alone proves the whole chain, so
this one closes that gap.

Every test here uses httpx.MockTransport -- a real httpx Client is
constructed and a real request is built and sent through httpx's request
pipeline (so header/param construction bugs would be caught), but no
socket ever leaves the machine. This is as close to "tested against the
real API" as is possible without actual network access to
api.data.gov.in, which this sandbox does not have (see the module's own
HONESTY NOTE docstring).

The success-path response body below is built to exactly match the
manually-verified real record for resource id
9ef84268-d588-465a-a308-a864a43d0070:
    State: Chattisgarh, Market: Kharsiya APMC, Commodity: Paddy(Common)
    Min 1790 / Max 1800 / Modal 1800, arrival_date 29/08/2026
"""
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx
import pytest

from app.services import live_market_data as lmd


VERIFIED_RECORD_RESPONSE = {
    "records": [
        {
            "state": "Chattisgarh",
            "district": "Raigarh",
            "market": "Kharsiya APMC",
            "commodity": "Paddy(Common)",
            "variety": "Common",
            "grade": "FAQ",
            "arrival_date": "29/08/2026",
            "min_price": "1790",
            "max_price": "1800",
            "modal_price": "1800",
        }
    ]
}


@pytest.fixture(autouse=True)
def _configured(monkeypatch):
    """Make is_configured() True and clear the module's request cache
    before/after each test so tests can't leak state into each other."""
    monkeypatch.setattr(lmd.settings, "data_gov_in_api_key", "test-key-not-real")
    monkeypatch.setattr(lmd.settings, "market_data_source", "live")
    monkeypatch.setattr(lmd.settings, "data_gov_in_resource_id", "9ef84268-d588-465a-a308-a864a43d0070")
    lmd._cache.clear()
    yield
    lmd._cache.clear()


_RealClient = httpx.Client


def _client_with_transport(handler):
    """Patch httpx.Client so live_market_data's `with httpx.Client(...)`
    uses our MockTransport instead of a real connection."""
    def _factory(*args, **kwargs):
        timeout = kwargs.get("timeout")
        return _RealClient(transport=httpx.MockTransport(handler), timeout=timeout)
    return _factory


def test_verified_real_record_is_parsed_correctly_and_uses_normalized_params(monkeypatch):
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(200, json=VERIFIED_RECORD_RESPONSE)

    monkeypatch.setattr(httpx, "Client", _client_with_transport(handler))

    outcome = lmd.fetch_live_price_status("Paddy", "Kharsiya APMC", state="Chhattisgarh")

    assert outcome["status"] == "ok"
    result = outcome["result"]
    assert result["modal_price"] == 1800.0
    assert result["min_price"] == 1790.0
    assert result["max_price"] == 1800.0
    assert result["arrival_date"] == "29/08/2026"
    # Display spelling restored for the UI, even though the source used "Chattisgarh"
    assert result["state"] == "Chhattisgarh"

    # The OUTGOING request must have used the exact source-spelling values,
    # never CropWise's display spelling / plain crop name.
    assert "filters%5Bstate%5D=Chattisgarh" in captured["url"] or "filters[state]=Chattisgarh" in captured["url"] or "Chattisgarh" in captured["url"]
    assert "Paddy%28Common%29" in captured["url"] or "Paddy(Common)" in captured["url"]
    assert "Chhattisgarh" not in captured["url"]  # must send source spelling, not display spelling


def test_empty_records_is_no_records_not_error(monkeypatch):
    monkeypatch.setattr(httpx, "Client", _client_with_transport(
        lambda req: httpx.Response(200, json={"records": []})
    ))
    outcome = lmd.fetch_live_price_status("Paddy", "Some Market", state="Chhattisgarh")
    assert outcome == {"status": "no_records", "result": None}


def test_non_200_is_error(monkeypatch):
    monkeypatch.setattr(httpx, "Client", _client_with_transport(
        lambda req: httpx.Response(500, text="internal server error")
    ))
    outcome = lmd.fetch_live_price_status("Paddy", "Kharsiya APMC", state="Chhattisgarh")
    assert outcome == {"status": "error", "result": None}


def test_malformed_json_is_error_not_a_crash(monkeypatch):
    def handler(request):
        return httpx.Response(200, content=b"not valid json {{{")
    monkeypatch.setattr(httpx, "Client", _client_with_transport(handler))
    outcome = lmd.fetch_live_price_status("Paddy", "Kharsiya APMC", state="Chhattisgarh")
    assert outcome == {"status": "error", "result": None}


def test_timeout_is_error_not_a_crash(monkeypatch):
    def handler(request):
        raise httpx.ConnectTimeout("simulated timeout, matching the real symptom reported in production")
    monkeypatch.setattr(httpx, "Client", _client_with_transport(handler))
    outcome = lmd.fetch_live_price_status("Paddy", "Kharsiya APMC", state="Chhattisgarh")
    assert outcome == {"status": "error", "result": None}


def test_not_configured_short_circuits_before_any_request(monkeypatch):
    monkeypatch.setattr(lmd.settings, "data_gov_in_api_key", "")
    called = {"n": 0}
    def handler(request):
        called["n"] += 1
        return httpx.Response(200, json=VERIFIED_RECORD_RESPONSE)
    monkeypatch.setattr(httpx, "Client", _client_with_transport(handler))
    outcome = lmd.fetch_live_price_status("Paddy", "Kharsiya APMC")
    assert outcome == {"status": "not_configured", "result": None}
    assert called["n"] == 0  # no request should even be attempted


def test_api_key_never_appears_in_a_raised_exception_message(monkeypatch):
    """The API key must never leak into logs/exceptions -- this module
    never raises at all (everything degrades to a status dict), which is
    itself the strongest guarantee against accidental key leakage via a
    traceback, but assert it explicitly."""
    def handler(request):
        raise httpx.ConnectError("boom")
    monkeypatch.setattr(httpx, "Client", _client_with_transport(handler))
    monkeypatch.setattr(lmd.settings, "data_gov_in_api_key", "SUPER-SECRET-KEY-VALUE")
    outcome = lmd.fetch_live_price_status("Paddy", "Kharsiya APMC")
    # Never raises, and the returned dict contains no trace of the key.
    assert "SUPER-SECRET-KEY-VALUE" not in json.dumps(outcome)


def test_commodity_and_state_normalization_layer_used_for_unmapped_crop(monkeypatch):
    """A crop with no explicit alias (e.g. 'Wheat') must pass through
    unchanged rather than being blocked or mangled."""
    captured = {}
    def handler(request):
        captured["url"] = str(request.url)
        return httpx.Response(200, json={"records": []})
    monkeypatch.setattr(httpx, "Client", _client_with_transport(handler))
    lmd.fetch_live_price_status("Wheat", "Some Market", state="Chhattisgarh")
    assert "Wheat" in captured["url"]
