"""Open-Meteo provider adapter: normalization, validation, retries, units.
All provider responses are MOCKED (this sandbox cannot reach Open-Meteo);
see the README section on weather for the separate live verification step."""
import os
import sys
from unittest.mock import MagicMock, patch

import httpx
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from tests.weather_fixtures import open_meteo_payload, DELETE
from app.services import open_meteo_provider as p


def _resp(status=200, payload=None, headers=None):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = payload
    r.headers = headers or {}
    return r


# ---- normalization ---------------------------------------------------------

def test_normalizes_current_daily_and_hourly():
    out = p.normalize_forecast(open_meteo_payload())
    assert out["timezone"] == "Asia/Kolkata" and out["utc_offset_seconds"] == 19800
    cur = out["current"]
    assert cur["temperature"] == 31.2 and cur["apparent_temperature"] == 34.0
    assert cur["wind_gusts_kmh"] == 22.0 and cur["pressure_hpa"] == 1008.0
    assert cur["is_day"] is True and cur["condition"] == "Mainly clear"
    assert len(out["forecast"]) == 7
    day0 = out["forecast"][0]
    assert day0["et0_mm"] == 4.5 and day0["sunrise"].endswith("06:05") and day0["wind_gusts_kmh"] == 22.0


def test_hourly_is_sliced_around_now_and_phased():
    out = p.normalize_forecast(open_meteo_payload())  # now = 14:30 local
    hourly = out["hourly"]
    assert hourly[0]["time"] == "2026-10-19T11:00"            # now-3h
    assert [h["phase"] for h in hourly[:5]] == ["past", "past", "past", "current", "future"]
    assert hourly[3]["time"] == "2026-10-19T14:00"            # hour containing "now"
    assert hourly[-1]["time"] == "2026-10-21T14:00"           # now+48h
    assert len(hourly) == 3 + 1 + 48


def test_hourly_is_day_follows_local_sunrise_sunset():
    hourly = p.normalize_forecast(open_meteo_payload())["hourly"]
    by_time = {h["time"]: h for h in hourly}
    assert by_time["2026-10-19T14:00"]["is_day"] is True
    assert by_time["2026-10-19T18:00"]["is_day"] is False     # after 17:40 sunset
    assert by_time["2026-10-20T05:00"]["is_day"] is False     # before 06:05 sunrise


def test_missing_optional_variables_become_none_not_errors():
    payload = open_meteo_payload(overrides={
        "daily.et0_fao_evapotranspiration": DELETE, "daily.sunrise": DELETE,
        "current.apparent_temperature": DELETE, "current.is_day": DELETE,
    })
    out = p.normalize_forecast(payload)
    assert out["forecast"][0]["et0_mm"] is None and out["forecast"][0]["sunrise"] is None
    assert out["current"]["apparent_temperature"] is None and out["current"]["is_day"] is None


def test_missing_hourly_block_gives_empty_hourly_but_keeps_everything_else():
    out = p.normalize_forecast(open_meteo_payload(hourly=False))
    assert out["hourly"] == [] and len(out["forecast"]) == 7


def test_null_values_inside_arrays_are_tolerated_in_hourly():
    payload = open_meteo_payload()
    payload["hourly"]["precipitation_probability"][15] = None
    payload["hourly"]["temperature_2m"][15] = None
    hourly = p.normalize_forecast(payload)["hourly"]
    row = next(h for h in hourly if h["time"] == "2026-10-19T15:00")
    assert row["rain_probability"] is None and row["temperature"] is None


@pytest.mark.parametrize("bad", [
    [], "oops", None, {}, {"current": {}, "daily": {"time": []}},
    {"current": {"temperature_2m": 1, "weather_code": 0, "wind_speed_10m": 1}, "daily": {"time": []}},
])
def test_malformed_payloads_raise_provider_error(bad):
    with pytest.raises(p.WeatherAPIError):
        p.normalize_forecast(bad)


def test_inconsistent_daily_array_lengths_rejected():
    payload = open_meteo_payload(overrides={"daily.precipitation_sum": [0.0, 1.0]})
    with pytest.raises(p.WeatherAPIError):
        p.normalize_forecast(payload)


def test_non_numeric_value_in_required_field_rejected():
    payload = open_meteo_payload(overrides={"current.temperature_2m": "hot"})
    with pytest.raises(p.WeatherAPIError):
        p.normalize_forecast(payload)


def test_unknown_weather_code_is_reported_unknown():
    assert p.condition_for_code(123) == "Unknown" and p.condition_for_code(None) == "Unknown"
    assert p.condition_for_code(65) == "Heavy rain" and p.condition_for_code(95) == "Thunderstorm"


# ---- units / timezone ------------------------------------------------------

def test_request_asks_for_indian_default_units_and_local_timezone():
    params = p.build_params(22.08, 82.14)
    assert params["temperature_unit"] == "celsius"
    assert params["wind_speed_unit"] == "kmh"
    assert params["precipitation_unit"] == "mm"
    assert params["timezone"] == "auto" and params["forecast_days"] == 7
    assert "et0_fao_evapotranspiration" in params["hourly"] and "et0_fao_evapotranspiration" in params["daily"]
    assert p.UNITS["temperature"] == "°C" and p.UNITS["wind"] == "km/h" and p.UNITS["precipitation"] == "mm"


def test_api_key_is_sent_only_when_configured_server_side():
    assert "apikey" not in p.build_params(1, 2)
    with patch.object(p.settings, "open_meteo_api_key", "SECRET-TEST-KEY", create=True):
        assert p.build_params(1, 2)["apikey"] == "SECRET-TEST-KEY"


# ---- coordinate validation -------------------------------------------------

@pytest.mark.parametrize("lat,lon", [(90, 180), (-90, -180), (22.08, 82.14), ("22.1", "82.2")])
def test_valid_coordinates_accepted(lat, lon):
    assert p.validate_coordinates(lat, lon) == (float(lat), float(lon))


@pytest.mark.parametrize("lat,lon", [
    (90.0001, 0), (-90.1, 0), (0, 180.0001), (0, -181), (float("nan"), 1), (1, float("inf")),
    (None, 1), ("abc", 1),
])
def test_invalid_coordinates_rejected(lat, lon):
    with pytest.raises(ValueError):
        p.validate_coordinates(lat, lon)


# ---- fetch: retries, rate limit, errors -----------------------------------

def test_fetch_success_returns_normalized_model():
    with patch("httpx.Client.get", return_value=_resp(200, open_meteo_payload())) as get:
        out = p.fetch_forecast(22.08, 82.14)
    assert out["current"]["temperature"] == 31.2 and get.call_count == 1


def test_server_error_is_retried_then_succeeds():
    seq = [_resp(503), _resp(502), _resp(200, open_meteo_payload())]
    with patch("httpx.Client.get", side_effect=seq) as get:
        out = p.fetch_forecast(22.08, 82.14)
    assert get.call_count == 3 and out["forecast"]


def test_persistent_server_error_gives_up_after_bounded_retries():
    with patch("httpx.Client.get", return_value=_resp(500)) as get:
        with pytest.raises(p.WeatherAPIError):
            p.fetch_forecast(22.08, 82.14)
    assert get.call_count == len(p.RETRY_BACKOFF_SECONDS) + 1


def test_timeout_is_retried_and_reported_without_leaking_details():
    with patch("httpx.Client.get", side_effect=httpx.ConnectTimeout("secret-host details")) as get:
        with pytest.raises(p.WeatherAPIError) as exc:
            p.fetch_forecast(22.08, 82.14)
    assert get.call_count == len(p.RETRY_BACKOFF_SECONDS) + 1
    assert "secret-host" not in str(exc.value)


def test_rate_limit_is_not_retried_and_carries_retry_after():
    with patch("httpx.Client.get", return_value=_resp(429, headers={"Retry-After": "120"})) as get:
        with pytest.raises(p.WeatherRateLimitError) as exc:
            p.fetch_forecast(22.08, 82.14)
    assert get.call_count == 1 and exc.value.retry_after == 120.0


def test_client_error_is_not_retried():
    with patch("httpx.Client.get", return_value=_resp(400)) as get:
        with pytest.raises(p.WeatherAPIError):
            p.fetch_forecast(22.08, 82.14)
    assert get.call_count == 1


def test_invalid_json_body_raises():
    r = _resp(200)
    r.json.side_effect = ValueError("bad json")
    with patch("httpx.Client.get", return_value=r):
        with pytest.raises(p.WeatherAPIError):
            p.fetch_forecast(22.08, 82.14)
