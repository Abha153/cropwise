"""Geocoding: search normalization, similarly named places, PIN/coordinate
input, validation, caching, reverse geocoding privacy and throttling.
Provider responses are mocked."""
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.services import geocoding_service as g


@pytest.fixture(autouse=True)
def _fresh(monkeypatch):
    g._search_cache.clear(); g._reverse_cache.clear()
    monkeypatch.setattr(g, "NOMINATIM_MIN_INTERVAL_SECONDS", 0.0)
    monkeypatch.setattr(g, "RETRY_BACKOFF_SECONDS", (0.0,))


def _resp(status=200, payload=None):
    r = MagicMock(); r.status_code = status; r.json.return_value = payload
    return r


BILASPUR = {"results": [
    {"id": 1, "name": "Bilaspur", "latitude": 22.0797, "longitude": 82.1409, "country": "India",
     "country_code": "IN", "admin1": "Chhattisgarh", "admin2": "Bilaspur", "timezone": "Asia/Kolkata"},
    {"id": 2, "name": "Bilaspur", "latitude": 31.3333, "longitude": 76.75, "country": "India",
     "country_code": "IN", "admin1": "Himachal Pradesh", "admin2": "Bilaspur", "timezone": "Asia/Kolkata"},
    {"id": 3, "name": "Bilaspur", "latitude": 28.4, "longitude": 77.3, "country": "India",
     "country_code": "IN", "admin1": "Haryana", "timezone": "Asia/Kolkata", "postcodes": ["122413"]},
]}


def test_similarly_named_places_are_distinguishable_by_region():
    with patch("httpx.Client.get", return_value=_resp(200, BILASPUR)):
        res = g.search_locations("Bilaspur")
    assert [r["admin1"] for r in res] == ["Chhattisgarh", "Himachal Pradesh", "Haryana"]
    labels = [r["label"] for r in res]
    assert len(set(labels)) == 3 and "Chhattisgarh" in labels[0] and labels[0].endswith("India")
    assert res[0]["latitude"] == 22.0797 and res[0]["timezone"] == "Asia/Kolkata"


def test_no_results_key_means_empty_list():
    with patch("httpx.Client.get", return_value=_resp(200, {"generationtime_ms": 0.4})):
        assert g.search_locations("zzzzzz") == []


def test_entries_without_usable_coordinates_or_name_are_dropped():
    data = {"results": [{"id": 1, "name": "A"}, {"id": 2, "latitude": 1, "longitude": 2},
                        {"id": 3, "name": "B", "latitude": 999, "longitude": 2},
                        {"id": 4, "name": "OK", "latitude": 1, "longitude": 2}]}
    assert [r["name"] for r in g.normalize_search_results(data)] == ["OK"]


@pytest.mark.parametrize("bad", [[], "x", {"results": "nope"}])
def test_malformed_search_payload_raises(bad):
    with pytest.raises(g.GeocodingError) as e:
        g.normalize_search_results(bad)
    assert e.value.code == "bad_response"


@pytest.mark.parametrize("q", ["", " ", "a", "x" * 101, "bad\x00query"])
def test_invalid_queries_rejected_before_any_network_call(q):
    with patch("httpx.Client.get") as get:
        with pytest.raises(g.GeocodingError) as e:
            g.search_locations(q)
    assert e.value.code == "bad_query" and get.call_count == 0


def test_postal_code_query_is_passed_through_to_the_provider():
    with patch("httpx.Client.get", return_value=_resp(200, BILASPUR)) as get:
        g.search_locations("495001")
    assert get.call_args.kwargs["params"]["name"] == "495001"


def test_latitude_longitude_input_becomes_a_coordinates_result_without_network():
    with patch("httpx.Client.get") as get:
        res = g.search_locations("22.0797, 82.1409")
    assert get.call_count == 0 and res[0]["kind"] == "coordinates"
    assert (res[0]["latitude"], res[0]["longitude"]) == (22.0797, 82.1409)


@pytest.mark.parametrize("q,expected", [
    ("22.08, 82.14", (22.08, 82.14)), ("-33.9 151.2", (-33.9, 151.2)),
    ("495001", None), ("91, 10", None), ("10, 181", None), ("Bilaspur", None),
])
def test_parse_coordinates(q, expected):
    assert g.parse_coordinates(q) == expected


def test_search_results_are_cached():
    with patch("httpx.Client.get", return_value=_resp(200, BILASPUR)) as get:
        g.search_locations("Bilaspur"); g.search_locations("bilaspur ")
    assert get.call_count == 1


def test_search_count_is_clamped():
    with patch("httpx.Client.get", return_value=_resp(200, BILASPUR)) as get:
        g.search_locations("Bilaspur", count=500)
    assert get.call_args.kwargs["params"]["count"] == 15


def test_rate_limit_and_server_errors_map_to_distinct_codes():
    with patch("httpx.Client.get", return_value=_resp(429)):
        with pytest.raises(g.GeocodingError) as e: g.search_locations("Bilaspur")
    assert e.value.code == "rate_limited"
    with patch("httpx.Client.get", return_value=_resp(503)) as get:
        with pytest.raises(g.GeocodingError) as e: g.search_locations("Raipur")
    assert e.value.code == "unavailable" and get.call_count == 2   # one retry


# ---- reverse geocoding ------------------------------------------------------

NOMINATIM = {"address": {"village": "Bilha", "state_district": "Bilaspur", "state": "Chhattisgarh", "country": "India"}}


def test_reverse_builds_a_readable_label():
    with patch("httpx.Client.get", return_value=_resp(200, NOMINATIM)):
        r = g.reverse_geocode(22.1503, 82.0504)
    assert r["name"] == "Bilha" and r["label"] == "Bilha, Bilaspur, Chhattisgarh, India"


def test_reverse_sends_rounded_coordinates_and_identifying_user_agent():
    with patch("httpx.Client.get", return_value=_resp(200, NOMINATIM)) as get:
        g.reverse_geocode(22.15034567, 82.05046789)
    params = get.call_args.kwargs["params"]
    assert (params["lat"], params["lon"]) == (22.15, 82.05)
    assert "CropWise" in get.call_args.kwargs["headers"]["User-Agent"]


def test_reverse_is_cached_per_rounded_location():
    with patch("httpx.Client.get", return_value=_resp(200, NOMINATIM)) as get:
        g.reverse_geocode(22.1501, 82.0501); g.reverse_geocode(22.1504, 82.0504)
    assert get.call_count == 1


def test_reverse_with_no_named_place_raises_instead_of_inventing_one():
    with patch("httpx.Client.get", return_value=_resp(200, {"address": {"country": "India"}})):
        with pytest.raises(g.GeocodingError): g.reverse_geocode(10.0, 70.0)
    with patch("httpx.Client.get", return_value=_resp(200, {"error": "Unable to geocode"})):
        with pytest.raises(g.GeocodingError): g.reverse_geocode(0.1, 0.1)


def test_reverse_out_of_range_rejected():
    with pytest.raises(g.GeocodingError): g.reverse_geocode(95, 10)
