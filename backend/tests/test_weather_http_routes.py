"""HTTP-level tests for the weather/geocoding routes via FastAPI's TestClient
(validation, status codes, safe error messages, response contract)."""
import os
import sys
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from tests.weather_fixtures import open_meteo_payload
from app.main import app
from app.services import weather_service as ws
from app.services import geocoding_service as g
from app.services import open_meteo_provider as p

client = TestClient(app)   # not used as a context manager: startup/seed hooks are not run


@pytest.fixture(autouse=True)
def _clean():
    ws._live_cache.clear(); ws._failure_cache.clear(); g._search_cache.clear(); g._reverse_cache.clear()


def _model():
    return p.normalize_forecast(open_meteo_payload())


def test_weather_contract_for_live_data():
    with patch.object(ws, "_fetch_live", return_value=_model()):
        r = client.get("/weather", params={"latitude": 22.08, "longitude": 82.14, "location": "Bilaspur"})
    assert r.status_code == 200
    body = r.json()
    for key in ("status", "source", "location", "current", "hourly", "forecast", "units",
                "attribution", "cache", "fetched_at", "timezone", "utc_offset_seconds"):
        assert key in body
    assert body["status"] == "LIVE" and "advisory" not in body


def test_advisory_included_on_request_with_crop_and_stage():
    with patch.object(ws, "_fetch_live", return_value=_model()):
        r = client.get("/weather", params={"latitude": 22.08, "longitude": 82.14, "include_advisory": "true",
                                           "crop": "Wheat", "growth_stage": "mid"})
    adv = r.json()["advisory"]
    assert adv["available"] and adv["crop"] == "Wheat" and adv["etc"]["kc"] == 1.15


@pytest.mark.parametrize("params", [
    {"latitude": 91, "longitude": 10}, {"latitude": -91, "longitude": 10},
    {"latitude": 10, "longitude": 181}, {"latitude": 10, "longitude": -181},
    {"latitude": 10}, {"longitude": 10}, {"latitude": "abc", "longitude": 10},
    {"latitude": "nan", "longitude": 10},
])
def test_invalid_coordinates_get_422_and_never_reach_the_provider(params):
    with patch.object(ws, "_fetch_live") as f:
        r = client.get("/weather", params=params)
    assert r.status_code == 422 and f.call_count == 0


def test_name_only_lookup_still_works_for_demo_locations():
    with patch.object(ws, "_fetch_live", side_effect=ws.WeatherAPIError("down")):
        r = client.get("/weather", params={"location": "Raipur"})
    assert r.status_code == 200 and r.json()["status"] == "DEMO"


def test_provider_outage_returns_200_with_unavailable_not_a_500():
    with patch.object(ws, "_fetch_live", side_effect=ws.WeatherAPIError("down")):
        r = client.get("/weather", params={"latitude": 10.5, "longitude": 76.2, "location": "Somewhere"})
    assert r.status_code == 200 and r.json()["status"] == "UNAVAILABLE"
    assert "down" not in r.text


# ---- geocoding routes ---------------------------------------------------------

def test_search_route_returns_regions_for_similar_names():
    payload = {"results": [
        {"id": 1, "name": "Bilaspur", "latitude": 22.08, "longitude": 82.14, "admin1": "Chhattisgarh", "country": "India", "country_code": "IN"},
        {"id": 2, "name": "Bilaspur", "latitude": 31.33, "longitude": 76.75, "admin1": "Himachal Pradesh", "country": "India", "country_code": "IN"}]}
    with patch.object(g, "_get_json", return_value=payload):
        r = client.get("/weather/geocode/search", params={"q": "Bilaspur"})
    assert r.status_code == 200
    labels = [x["label"] for x in r.json()["results"]]
    assert labels[0] != labels[1] and "Chhattisgarh" in labels[0]


def test_search_route_validation():
    assert client.get("/weather/geocode/search").status_code == 422
    assert client.get("/weather/geocode/search", params={"q": "a"}).status_code == 422
    assert client.get("/weather/geocode/search", params={"q": "x" * 121}).status_code == 422
    assert client.get("/weather/geocode/search", params={"q": "Raipur", "count": 99}).status_code == 422
    assert client.get("/weather/geocode/search", params={"q": "Raipur", "country_code": "IND"}).status_code == 422


def test_search_provider_errors_map_to_safe_http_errors():
    for code, status in (("rate_limited", 429), ("unavailable", 503), ("bad_response", 502)):
        with patch.object(g, "search_locations", side_effect=g.GeocodingError(code, "internal detail host=secret")):
            r = client.get("/weather/geocode/search", params={"q": "Raipur"})
        assert r.status_code == status and "secret" not in r.text


def test_search_coordinates_input_needs_no_provider():
    with patch.object(g, "_get_json") as gj:
        r = client.get("/weather/geocode/search", params={"q": "22.08, 82.14"})
    assert gj.call_count == 0 and r.json()["results"][0]["kind"] == "coordinates"


def test_reverse_route_success_and_validation():
    nominatim = {"address": {"village": "Bilha", "state_district": "Bilaspur", "state": "Chhattisgarh", "country": "India"}}
    with patch.object(g, "_get_json", return_value=nominatim):
        r = client.get("/weather/geocode/reverse", params={"latitude": 22.15, "longitude": 82.05})
    assert r.status_code == 200 and r.json()["label"].startswith("Bilha")
    assert client.get("/weather/geocode/reverse", params={"latitude": 95, "longitude": 10}).status_code == 422
    assert client.get("/weather/geocode/reverse", params={"latitude": 10}).status_code == 422


def test_reverse_failure_is_a_503_so_the_ui_can_show_coordinates_instead():
    with patch.object(g, "_get_json", return_value={"error": "Unable to geocode"}):
        r = client.get("/weather/geocode/reverse", params={"latitude": 0.5, "longitude": 0.5})
    assert r.status_code == 503


def test_farmer_endpoint_still_requires_auth():
    assert client.get("/weather/farmer").status_code in (401, 403)
