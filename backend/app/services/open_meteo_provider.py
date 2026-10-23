"""
Open-Meteo weather provider adapter.

This module is the ONLY place that knows Open-Meteo's request/response
shape. It turns a provider response into CropWise's internal weather model
(see `normalize_forecast`), so weather_service.py, the advisory engine and
the frontend never depend on provider field names. To swap or add a
provider, implement a module exposing `fetch_forecast(lat, lon)` that
returns the same normalized dict and raises the same exceptions.

Contract: https://open-meteo.com/en/docs (Forecast API). No API key is
needed for the free tier, which Open-Meteo licenses for NON-COMMERCIAL use
only -- a commercial deployment must use their paid plan (set
OPEN_METEO_API_KEY and OPEN_METEO_BASE_URL, see backend/.env.example).
Data is CC BY 4.0: attribution is returned in `attribution` and rendered
by the UI.

Normalized model (all numbers are floats rounded for display, None when the
provider omitted the value):

    {
      "timezone": "Asia/Kolkata", "utc_offset_seconds": 19800,
      "current": {...}, "hourly": [...], "forecast": [...]  # forecast = daily
    }

"current" is Open-Meteo's model-based current conditions (a blend of
station/satellite analysis and model output for the grid cell), NOT a
reading from a weather station at the user's exact spot. The UI labels it
accordingly. Hourly and daily blocks are forecasts.
"""
import datetime as dt
import math
import time
from typing import Optional

import httpx

from app.config import settings

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
FORECAST_DAYS = 7
REQUEST_TIMEOUT_SECONDS = 6.0
# Retries apply to timeouts, connection errors and 5xx only. A 429 is never
# retried inside the request (that would just burn more of the quota); it is
# raised as WeatherRateLimitError so the caller can serve cached data.
RETRY_BACKOFF_SECONDS = (0.4, 0.9)

HOURS_PAST = 3     # hours before "now" kept so the UI can show past vs future
HOURS_AHEAD = 48   # hours after "now" kept (UI shows 24; advisory uses 48)

CURRENT_VARS = (
    "temperature_2m,apparent_temperature,relative_humidity_2m,is_day,"
    "precipitation,rain,weather_code,cloud_cover,pressure_msl,"
    "wind_speed_10m,wind_direction_10m,wind_gusts_10m"
)
HOURLY_VARS = (
    "temperature_2m,apparent_temperature,relative_humidity_2m,"
    "precipitation_probability,precipitation,weather_code,"
    "wind_speed_10m,wind_gusts_10m,et0_fao_evapotranspiration"
)
DAILY_VARS = (
    "weather_code,temperature_2m_max,temperature_2m_min,"
    "precipitation_probability_max,precipitation_sum,wind_speed_10m_max,"
    "wind_gusts_10m_max,sunrise,sunset,et0_fao_evapotranspiration"
)

UNITS = {
    "temperature": "°C", "wind": "km/h", "precipitation": "mm",
    "pressure": "hPa", "et0": "mm", "humidity": "%",
}

ATTRIBUTION = {
    "provider": "Open-Meteo.com",
    "url": "https://open-meteo.com/",
    "license": "CC BY 4.0",
    "current_note": "Current conditions are model-based for the surrounding grid cell, not a reading from a station at your exact location.",
}

# ---------------------------------------------------------------------------
# WMO weather code -> condition text (single source of truth; the frontend
# only maps the raw code to an icon).
# ---------------------------------------------------------------------------
_WMO_CONDITIONS = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Depositing rime fog",
    51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
    56: "Light freezing drizzle", 57: "Dense freezing drizzle",
    61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    66: "Light freezing rain", 67: "Heavy freezing rain",
    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow", 77: "Snow grains",
    80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
    85: "Slight snow showers", 86: "Heavy snow showers",
    95: "Thunderstorm", 96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail",
}


def condition_for_code(code) -> str:
    try:
        return _WMO_CONDITIONS.get(int(code), "Unknown")
    except (TypeError, ValueError):
        return "Unknown"


class WeatherAPIError(Exception):
    """Any live-fetch failure: network, timeout, HTTP status, or a response
    that doesn't match the expected shape."""


class WeatherRateLimitError(WeatherAPIError):
    """Provider answered HTTP 429 (quota / rate limit)."""

    def __init__(self, message="rate limited", retry_after: Optional[float] = None):
        super().__init__(message)
        self.retry_after = retry_after


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def validate_coordinates(latitude, longitude) -> tuple:
    """Returns (lat, lon) as floats or raises ValueError. NaN/inf and
    out-of-range values are rejected."""
    try:
        lat, lon = float(latitude), float(longitude)
    except (TypeError, ValueError) as e:
        raise ValueError("latitude and longitude must be numbers") from e
    if not (math.isfinite(lat) and math.isfinite(lon)):
        raise ValueError("latitude and longitude must be finite numbers")
    if not -90.0 <= lat <= 90.0:
        raise ValueError("latitude must be between -90 and 90")
    if not -180.0 <= lon <= 180.0:
        raise ValueError("longitude must be between -180 and 180")
    return lat, lon


def _num(value, ndigits=1):
    """float(value) rounded, or None when missing/non-numeric/NaN."""
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(f):
        return None
    return round(f, ndigits)


def _series(block: dict, key: str, n: int) -> list:
    """A list of exactly n entries for `key` (None-padded when the provider
    omitted the variable or returned a short array)."""
    raw = block.get(key)
    if not isinstance(raw, list):
        return [None] * n
    return (raw + [None] * n)[:n]


def _parse_local(ts: Optional[str]) -> Optional[dt.datetime]:
    if not isinstance(ts, str):
        return None
    try:
        return dt.datetime.fromisoformat(ts)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Normalization (pure -- unit tested without any network)
# ---------------------------------------------------------------------------

def normalize_forecast(data: dict) -> dict:
    """Validates an Open-Meteo forecast payload and converts it to the
    internal model. Raises WeatherAPIError on a malformed payload."""
    if not isinstance(data, dict):
        raise WeatherAPIError("response is not a JSON object")
    current = data.get("current")
    daily = data.get("daily")
    if not isinstance(current, dict) or not isinstance(daily, dict):
        raise WeatherAPIError("missing current/daily blocks")

    required_daily = (
        "time", "weather_code", "temperature_2m_max", "temperature_2m_min",
        "precipitation_probability_max", "precipitation_sum", "wind_speed_10m_max",
    )
    for key in required_daily:
        if key not in daily or not isinstance(daily[key], list):
            raise WeatherAPIError(f"daily block missing/invalid field: {key}")
    lengths = {len(daily[k]) for k in required_daily}
    if len(lengths) != 1 or lengths == {0}:
        raise WeatherAPIError("daily arrays have inconsistent/zero length")
    for key in ("temperature_2m", "weather_code", "wind_speed_10m"):
        if current.get(key) is None:
            raise WeatherAPIError(f"current block missing field: {key}")

    n = len(daily["time"])
    try:
        sunrise = _series(daily, "sunrise", n)
        sunset = _series(daily, "sunset", n)
        gust_max = _series(daily, "wind_gusts_10m_max", n)
        et0 = _series(daily, "et0_fao_evapotranspiration", n)
        forecast = []
        for i in range(n):
            forecast.append({
                "date": daily["time"][i],
                "weather_code": int(daily["weather_code"][i]),
                "condition": condition_for_code(daily["weather_code"][i]),
                "temp_min": round(float(daily["temperature_2m_min"][i]), 1),
                "temp_max": round(float(daily["temperature_2m_max"][i]), 1),
                "rainfall_probability": round(float(daily["precipitation_probability_max"][i]), 0),
                "rainfall_mm": round(float(daily["precipitation_sum"][i]), 1),
                "wind_speed_kmh": round(float(daily["wind_speed_10m_max"][i]), 1),
                "wind_gusts_kmh": _num(gust_max[i]),
                "sunrise": sunrise[i],
                "sunset": sunset[i],
                "et0_mm": _num(et0[i], 2),
                "humidity": None,  # not part of the daily block
            })
        current_out = {
            "observed_at": current.get("time"),
            "temperature": round(float(current["temperature_2m"]), 1),
            "apparent_temperature": _num(current.get("apparent_temperature")),
            "humidity": _num(current.get("relative_humidity_2m"), 0),
            "precipitation_mm": _num(current.get("precipitation")) or 0.0,
            "rain_mm": _num(current.get("rain")),
            "weather_code": int(current["weather_code"]),
            "condition": condition_for_code(current["weather_code"]),
            "wind_speed_kmh": round(float(current["wind_speed_10m"]), 1),
            "wind_direction_deg": _num(current.get("wind_direction_10m"), 0),
            "wind_gusts_kmh": _num(current.get("wind_gusts_10m")),
            "cloud_cover_pct": _num(current.get("cloud_cover"), 0),
            "pressure_hpa": _num(current.get("pressure_msl"), 0),
            "is_day": (bool(current["is_day"]) if current.get("is_day") is not None else None),
        }
    except (KeyError, TypeError, ValueError) as e:
        raise WeatherAPIError(f"malformed values: {e}") from e

    hourly_out = _normalize_hourly(data.get("hourly"), current_out["observed_at"], forecast)

    return {
        "timezone": data.get("timezone"),
        "utc_offset_seconds": data.get("utc_offset_seconds") if isinstance(data.get("utc_offset_seconds"), int) else None,
        "current": current_out,
        "hourly": hourly_out,
        "forecast": forecast,
    }


def _normalize_hourly(hourly, now_local: Optional[str], daily: list) -> list:
    """Slices the provider's 168 hourly rows down to [now-3h, now+48h] and
    tags each with phase = past | current | future. Returns [] (never raises)
    when the hourly block is missing or unusable, so the rest of the
    dashboard still renders."""
    if not isinstance(hourly, dict) or not isinstance(hourly.get("time"), list) or not hourly["time"]:
        return []
    now = _parse_local(now_local)
    if now is None:
        return []
    n = len(hourly["time"])
    cols = {
        "temperature": _series(hourly, "temperature_2m", n),
        "apparent_temperature": _series(hourly, "apparent_temperature", n),
        "humidity": _series(hourly, "relative_humidity_2m", n),
        "rain_probability": _series(hourly, "precipitation_probability", n),
        "rainfall_mm": _series(hourly, "precipitation", n),
        "weather_code": _series(hourly, "weather_code", n),
        "wind_speed_kmh": _series(hourly, "wind_speed_10m", n),
        "wind_gusts_kmh": _series(hourly, "wind_gusts_10m", n),
        "et0_mm": _series(hourly, "et0_fao_evapotranspiration", n),
    }
    sun = {}
    for d in daily:
        sr, ss = _parse_local(d.get("sunrise")), _parse_local(d.get("sunset"))
        if sr and ss:
            sun[d["date"]] = (sr, ss)

    current_hour = now.replace(minute=0, second=0, microsecond=0)
    start = current_hour - dt.timedelta(hours=HOURS_PAST)
    end = current_hour + dt.timedelta(hours=HOURS_AHEAD)
    out = []
    for i, ts in enumerate(hourly["time"]):
        t = _parse_local(ts)
        if t is None or t < start or t > end:
            continue
        code = cols["weather_code"][i]
        try:
            code_i = int(code) if code is not None else None
        except (TypeError, ValueError):
            code_i = None
        sunrise_sunset = sun.get(t.date().isoformat())
        is_day = (sunrise_sunset[0] <= t <= sunrise_sunset[1]) if sunrise_sunset else None
        out.append({
            "time": ts,
            "phase": "past" if t < current_hour else "current" if t == current_hour else "future",
            "temperature": _num(cols["temperature"][i]),
            "apparent_temperature": _num(cols["apparent_temperature"][i]),
            "humidity": _num(cols["humidity"][i], 0),
            "rain_probability": _num(cols["rain_probability"][i], 0),
            "rainfall_mm": _num(cols["rainfall_mm"][i]),
            "weather_code": code_i,
            "condition": condition_for_code(code_i) if code_i is not None else None,
            "wind_speed_kmh": _num(cols["wind_speed_kmh"][i]),
            "wind_gusts_kmh": _num(cols["wind_gusts_kmh"][i]),
            "et0_mm": _num(cols["et0_mm"][i], 2),
            "is_day": is_day,
        })
    return out


# ---------------------------------------------------------------------------
# Fetch
# ---------------------------------------------------------------------------

def build_params(latitude: float, longitude: float) -> dict:
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": CURRENT_VARS,
        "hourly": HOURLY_VARS,
        "daily": DAILY_VARS,
        "temperature_unit": "celsius",
        "wind_speed_unit": "kmh",
        "precipitation_unit": "mm",
        "timezone": "auto",
        "forecast_days": FORECAST_DAYS,
    }
    api_key = getattr(settings, "open_meteo_api_key", "")
    if api_key:
        params["apikey"] = api_key  # server-side only; never sent to the browser
    return params


def _base_url() -> str:
    return getattr(settings, "open_meteo_base_url", "") or OPEN_METEO_URL


def _retry_after(resp) -> Optional[float]:
    try:
        return float(resp.headers.get("Retry-After"))
    except (AttributeError, TypeError, ValueError):
        return None


def fetch_forecast(latitude: float, longitude: float) -> dict:
    """One provider round trip (with bounded retries) -> normalized model.
    Coordinates must already be validated by the caller."""
    params = build_params(latitude, longitude)
    attempts = len(RETRY_BACKOFF_SECONDS) + 1
    last_error: Exception = WeatherAPIError("no attempt made")
    for attempt in range(attempts):
        try:
            with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS) as client:
                resp = client.get(_base_url(), params=params)
        except httpx.HTTPError as e:
            last_error = WeatherAPIError(f"network error: {type(e).__name__}")
        else:
            status = resp.status_code
            if status == 200:
                try:
                    payload = resp.json()
                except ValueError as e:
                    raise WeatherAPIError("invalid JSON from provider") from e
                return normalize_forecast(payload)
            if status == 429:
                raise WeatherRateLimitError("provider rate limit reached", _retry_after(resp))
            if status < 500:
                # 4xx other than 429 is a request problem; retrying won't help.
                raise WeatherAPIError(f"HTTP {status}")
            last_error = WeatherAPIError(f"HTTP {status}")
        if attempt < attempts - 1:
            time.sleep(RETRY_BACKOFF_SECONDS[attempt])
    raise last_error
