"""weather_service orchestration: fresh/stale cache, rate limiting, request
deduplication, privacy of logs and provider coordinates, status contract."""
import logging
import os
import sys
import threading
import time
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from tests.weather_fixtures import open_meteo_payload
from app.services import weather_service as ws
from app.services import open_meteo_provider as p

LAT, LON = 22.0797, 82.1409


@pytest.fixture(autouse=True)
def _clean_state():
    ws._live_cache.clear(); ws._failure_cache.clear(); ws._inflight_locks.clear()
    yield
    ws._live_cache.clear(); ws._failure_cache.clear(); ws._inflight_locks.clear()


def _model():
    return p.normalize_forecast(open_meteo_payload())


def test_first_call_is_live_and_reports_cache_state_and_timestamp():
    with patch.object(ws, "_fetch_live", return_value=_model()) as f:
        r = ws.get_weather(LAT, LON, "Bilaspur")
    assert r["status"] == "LIVE" and r["cache"]["state"] == "live" and f.call_count == 1
    assert r["fetched_at"].endswith("+00:00") and r["cache"]["age_seconds"] == 0
    assert r["attribution"]["provider"] == "Open-Meteo.com" and r["units"]["wind"] == "km/h"
    assert r["hourly"] and r["forecast"] and r["timezone"] == "Asia/Kolkata"


def test_second_call_within_ttl_is_a_cache_hit_labelled_fresh():
    with patch.object(ws, "_fetch_live", return_value=_model()) as f:
        ws.get_weather(LAT, LON, "Bilaspur")
        r = ws.get_weather(LAT, LON, "Bilaspur")
    assert f.call_count == 1 and r["status"] == "LIVE" and r["cache"]["state"] == "fresh"


def test_nearby_coordinates_share_one_provider_call():
    with patch.object(ws, "_fetch_live", return_value=_model()) as f:
        ws.get_weather(22.0797, 82.1409, "A")
        ws.get_weather(22.0801, 82.1412, "B")   # same ~1 km grid cell
        ws.get_weather(23.5, 82.1409, "C")      # different cell
    assert f.call_count == 2


def test_provider_receives_rounded_coordinates_only():
    with patch.object(p, "fetch_forecast", return_value=_model()) as f:
        ws.get_weather(22.07974321, 82.14093456, "x")
    assert f.call_args.args == (22.08, 82.14)


def test_expired_cache_is_refreshed_when_provider_works():
    with patch.object(ws, "_fetch_live", return_value=_model()) as f:
        ws.get_weather(LAT, LON, "x")
        key = ws._cache_key(LAT, LON)
        ts, val = ws._live_cache[key]
        ws._live_cache[key] = (ts - ws.LIVE_CACHE_TTL_SECONDS - 5, val)
        r = ws.get_weather(LAT, LON, "x")
    assert f.call_count == 2 and r["cache"]["state"] == "live"


def test_provider_failure_serves_stale_copy_clearly_labelled_with_age():
    with patch.object(ws, "_fetch_live", return_value=_model()):
        ws.get_weather(LAT, LON, "x")
    key = ws._cache_key(LAT, LON)
    ts, val = ws._live_cache[key]
    ws._live_cache[key] = (ts - 3 * 3600, val)   # 3 h old: expired but within stale window
    with patch.object(ws, "_fetch_live", side_effect=ws.WeatherAPIError("down")):
        r = ws.get_weather(LAT, LON, "x")
    assert r["status"] == "STALE" and r["cache"]["state"] == "stale"
    assert 3 * 3600 <= r["cache"]["age_seconds"] < 3 * 3600 + 60
    assert "last saved forecast" in r["notice"] and r["current"]["temperature"] == 31.2


def test_rate_limit_serves_stale_and_backs_off_without_hammering_provider():
    with patch.object(ws, "_fetch_live", return_value=_model()):
        ws.get_weather(LAT, LON, "x")
    key = ws._cache_key(LAT, LON)
    ts, val = ws._live_cache[key]
    ws._live_cache[key] = (ts - 3600, val)
    with patch.object(ws, "_fetch_live", side_effect=ws.WeatherRateLimitError("429", 90)) as f:
        r1 = ws.get_weather(LAT, LON, "x")
        r2 = ws.get_weather(LAT, LON, "x")
    assert r1["status"] == r2["status"] == "STALE" and "rate limiting" in r1["notice"]
    assert f.call_count == 1   # second request honoured the back-off window


def test_cache_older_than_stale_window_is_not_served():
    with patch.object(ws, "_fetch_live", return_value=_model()):
        ws.get_weather(LAT, LON, "Nowhere")
    key = ws._cache_key(LAT, LON)
    ts, val = ws._live_cache[key]
    ws._live_cache[key] = (ts - ws.STALE_MAX_AGE_SECONDS - 10, val)
    with patch.object(ws, "_fetch_live", side_effect=ws.WeatherAPIError("down")):
        r = ws.get_weather(LAT, LON, "Nowhere")
    assert r["status"] == "UNAVAILABLE" and r["current"] is None and r["forecast"] == []


def test_no_cache_and_no_demo_match_is_unavailable_never_fabricated():
    with patch.object(ws, "_fetch_live", side_effect=ws.WeatherAPIError("down")):
        r = ws.get_weather(10.5, 76.2, "Some Village")
    assert r["status"] == "UNAVAILABLE" and r["source"] is None and r["hourly"] == []


def test_demo_fallback_is_still_labelled_demo_and_has_no_fake_hourly_or_timestamp():
    with patch.object(ws, "_fetch_live", side_effect=ws.WeatherAPIError("down")):
        r = ws.get_weather(LAT, LON, "Bilaspur")
    assert r["status"] == "DEMO" and r["source"] == "CropWise Demo Dataset"
    assert r["hourly"] == [] and r["fetched_at"] is None and r["cache"] is None


def test_out_of_range_coordinates_never_reach_the_provider():
    with patch.object(ws, "_fetch_live") as f:
        r = ws.get_weather(95.0, 10.0, "Nowhere")
    assert f.call_count == 0 and r["status"] == "UNAVAILABLE"


def test_concurrent_identical_requests_share_a_single_provider_call():
    calls = []
    gate = threading.Event()

    def slow_fetch(lat, lon):
        calls.append(1)
        gate.wait(1.0)
        return _model()

    results = []
    with patch.object(ws, "_fetch_live", side_effect=slow_fetch):
        threads = [threading.Thread(target=lambda: results.append(ws.get_weather(LAT, LON, "x"))) for _ in range(6)]
        for t in threads: t.start()
        time.sleep(0.2); gate.set()
        for t in threads: t.join(5)
    assert len(calls) == 1 and len(results) == 6
    assert all(r["status"] == "LIVE" for r in results)


def test_failures_are_logged_without_precise_coordinates(caplog):
    caplog.set_level(logging.DEBUG, logger="cropwise")
    with patch.object(ws, "_fetch_live", side_effect=ws.WeatherAPIError("down")):
        ws.get_weather(22.07974321, 82.14093456, "x")
    text = " ".join(r.getMessage() for r in caplog.records)
    assert "22.07974321" not in text and "82.14093456" not in text


def test_cache_is_bounded():
    with patch.object(ws, "_fetch_live", return_value=_model()):
        for i in range(ws._CACHE_MAX_ENTRIES + 25):
            ws.get_weather(10 + (i % 70) + (i // 70) * 0.01, 70 + (i % 40) + (i // 40) * 0.01, "x")
    assert len(ws._live_cache) <= ws._CACHE_MAX_ENTRIES


def test_derive_weather_risk_treats_stale_as_live_data():
    with patch.object(ws, "_fetch_live", return_value=_model()):
        r = ws.get_weather(LAT, LON, "x")
    r["status"] = "STALE"
    risk, note = ws.derive_weather_risk(r)
    assert risk in ("Low", "Medium", "High") and note.startswith("Live forecast")
