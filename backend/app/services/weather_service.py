"""
Weather service -- LIVE (Open-Meteo) with a deterministic SEEDED DEMO
fallback, never a randomly-generated one.

CONTRACT (see app/routers/weather.py for the HTTP surface):

    get_weather(latitude, longitude, location_name) -> dict with:
        status: "LIVE" | "DEMO" | "UNAVAILABLE"
        source: "Open-Meteo" | "CropWise Demo Dataset" | None
        location: {name, latitude, longitude}
        current: {...} | None
        forecast: [ {date, weather_code, condition, temp_min, temp_max,
                     humidity, rainfall_probability, rainfall_mm,
                     wind_speed_kmh}, ... up to 7 entries ] | []

FLOW
    try live (Open-Meteo)
        -> validate response shape
        -> return LIVE
    except (network error, timeout, HTTP error, malformed response)
        -> look up deterministic seeded fallback for location_name
        -> if found: return DEMO
        -> if not found: return UNAVAILABLE

NOTE: the provider request/normalization now lives in
app/services/open_meteo_provider.py. The honesty note below still applies.

HONESTY (read before trusting this blindly): this sandboxed development
environment cannot reach api.open-meteo.com at all -- confirmed both via
direct network attempts (blocked, not on this environment's allowlist)
and via api.open-meteo.com's own robots.txt (disallows automated
fetching, so even the assistant's web-fetch tool was refused). The LIVE
code path below is written strictly to Open-Meteo's public, versioned,
well-documented Forecast API contract (https://open-meteo.com/en/docs --
no API key required for the free/non-commercial tier) and is covered by
mocked-response tests that exercise real Open-Meteo-shaped JSON, but it
has NOT been exercised against a real live HTTP round trip from this
environment. Please verify once deployed somewhere with outbound
internet access, and report back if Open-Meteo's schema has changed.

DATA INTEGRITY: the DEMO dataset below is a small, fixed, hand-authored
table -- no random.random(), no per-request generation, no per-day
drift. The same location always returns the same 7-day demo forecast
until this file is edited. Every seeded location below corresponds to an
actual DEMO_FARMERS location in app/mock_data/demo_users.py (Bilaspur,
Raigarh, Durg, Rajnandgaon, Mahasamund, Korba, Ambikapur, Jagdalpur,
Bilha, Raipur) -- no farmer's location was invented or changed to make
weather "available".
"""
import datetime as dt
import threading
import time
from typing import Optional

from app.config import logger
from app.services import open_meteo_provider as provider
# Re-exported: existing callers/tests import these names from this module.
from app.services.open_meteo_provider import (  # noqa: F401
    WeatherAPIError, WeatherRateLimitError, condition_for_code, validate_coordinates,
)

OPEN_METEO_URL = provider.OPEN_METEO_URL
FORECAST_DAYS = provider.FORECAST_DAYS
LIVE_CACHE_TTL_SECONDS = 20 * 60   # data younger than this is served as "fresh"
# When the provider is down or rate limiting us, an expired entry up to this
# old is still served -- but labelled STALE with its age, never as new data.
STALE_MAX_AGE_SECONDS = 6 * 60 * 60
REQUEST_TIMEOUT_SECONDS = provider.REQUEST_TIMEOUT_SECONDS

# ---------------------------------------------------------------------------
# LIVE fetch + cache
# ---------------------------------------------------------------------------

# (rounded_lat, rounded_lon) -> (fetched_at_epoch, normalized_result)
# Entries are kept past their TTL on purpose, so they can be served as STALE
# when the provider fails. Bounded by _CACHE_MAX_ENTRIES.
_live_cache: dict = {}
_CACHE_MAX_ENTRIES = 500

# Failures are not written into _live_cache. Without a short negative cache,
# an unreachable/slow provider makes every dashboard load re-pay the full
# timeout instead of failing fast after the first attempt.
_FAILURE_CACHE_TTL_SECONDS = 60.0
_failure_cache: dict = {}

# Request deduplication: concurrent requests for the same grid cell share one
# provider call instead of each hitting Open-Meteo.
_inflight_locks: dict = {}
_inflight_guard = threading.Lock()


def _cache_key(lat: float, lon: float):
    # ~1.1 km precision. Nearby requests share an entry, and it is also the
    # precision actually sent to the provider (privacy: no need for more --
    # the forecast grid is several km wide).
    return (round(lat, 2), round(lon, 2))


def _lock_for(key):
    with _inflight_guard:
        return _inflight_locks.setdefault(key, threading.Lock())


def _store(key, result):
    if len(_live_cache) >= _CACHE_MAX_ENTRIES:
        oldest = min(_live_cache, key=lambda k: _live_cache[k][0])
        _live_cache.pop(oldest, None)
    _live_cache[key] = (time.time(), result)


def _fetch_live(latitude: float, longitude: float) -> dict:
    """Provider round trip returning the normalized model. Kept as a thin
    seam (tests patch it) over the provider adapter."""
    rlat, rlon = _cache_key(latitude, longitude)
    return provider.fetch_forecast(rlat, rlon)


def _cache_meta(fetched_at: float, state: str) -> dict:
    return {
        "state": state,  # "live" (just fetched) | "fresh" (cache hit) | "stale"
        "fetched_at": dt.datetime.fromtimestamp(fetched_at, dt.timezone.utc).isoformat(timespec="seconds"),
        "age_seconds": max(0, int(time.time() - fetched_at)),
    }


def _live_payload(result: dict, loc_out: dict, status: str, cache: dict, notice: Optional[str] = None) -> dict:
    out = {
        "status": status, "source": "Open-Meteo", "location": loc_out,
        "units": provider.UNITS, "attribution": provider.ATTRIBUTION,
        "cache": cache, "fetched_at": cache["fetched_at"], "notice": notice,
        **result,
    }
    return out


# ---------------------------------------------------------------------------
# DEMO fallback -- deterministic, hand-authored, never random
# ---------------------------------------------------------------------------

def _demo_day(offset, temp_max, temp_min, humidity, rain_prob, rain_mm, wind, code):
    base = dt.date(2026, 9, 2)  # fixed anchor -- see module docstring: this
    # is a deterministic table, not "today's real date" recomputed live.
    return {
        "date": (base + dt.timedelta(days=offset)).isoformat(),
        "weather_code": code,
        "condition": condition_for_code(code),
        "temp_min": temp_min, "temp_max": temp_max,
        "humidity": humidity,
        "rainfall_probability": rain_prob, "rainfall_mm": rain_mm,
        "wind_speed_kmh": wind,
    }


# Each location: 7 hand-authored, internally-consistent days (high rain
# probability days use a rain/drizzle/thunderstorm WMO code, never
# "Clear sky" -- see module docstring's "impossible combinations" rule).
# Coordinates match app/mock_data/demo_users.py exactly.
_SEEDED_WEATHER = {
    "bilaspur": {
        "display_name": "Bilaspur, Chhattisgarh", "latitude": 22.0797, "longitude": 82.1409,
        "days": [
            _demo_day(0, 33.0, 24.0, 68, 10, 0.0, 9.0, 1),
            _demo_day(1, 34.0, 25.0, 65, 5, 0.0, 8.0, 0),
            _demo_day(2, 32.0, 24.5, 74, 40, 3.0, 12.0, 61),
            _demo_day(3, 29.0, 23.0, 85, 78, 22.0, 18.0, 63),
            _demo_day(4, 28.5, 22.5, 88, 82, 30.0, 21.0, 80),
            _demo_day(5, 30.0, 23.5, 76, 45, 6.0, 14.0, 61),
            _demo_day(6, 32.5, 24.0, 66, 15, 0.5, 10.0, 2),
        ],
    },
    "raigarh": {
        "display_name": "Raigarh, Chhattisgarh", "latitude": 21.8974, "longitude": 83.3950,
        "days": [
            _demo_day(0, 32.5, 24.5, 70, 15, 0.0, 10.0, 2),
            _demo_day(1, 31.0, 24.0, 78, 55, 8.0, 15.0, 61),
            _demo_day(2, 29.5, 23.0, 84, 70, 18.0, 17.0, 63),
            _demo_day(3, 30.0, 23.5, 72, 35, 2.0, 13.0, 51),
            _demo_day(4, 33.0, 25.0, 60, 8, 0.0, 9.0, 0),
            _demo_day(5, 33.5, 25.5, 58, 5, 0.0, 8.0, 1),
            _demo_day(6, 31.5, 24.0, 68, 20, 1.0, 11.0, 2),
        ],
    },
    "durg": {
        "display_name": "Durg, Chhattisgarh", "latitude": 21.1904, "longitude": 81.2849,
        "days": [
            _demo_day(0, 34.5, 25.5, 55, 5, 0.0, 7.0, 0),
            _demo_day(1, 35.0, 26.0, 52, 5, 0.0, 7.0, 0),
            _demo_day(2, 34.0, 25.5, 60, 15, 0.0, 9.0, 1),
            _demo_day(3, 31.0, 24.0, 76, 60, 12.0, 16.0, 61),
            _demo_day(4, 29.5, 23.0, 83, 72, 20.0, 19.0, 63),
            _demo_day(5, 31.5, 24.0, 70, 30, 2.0, 12.0, 51),
            _demo_day(6, 33.5, 25.0, 58, 10, 0.0, 8.0, 1),
        ],
    },
    "rajnandgaon": {
        "display_name": "Rajnandgaon, Chhattisgarh", "latitude": 21.0972, "longitude": 81.0388,
        "days": [
            _demo_day(0, 33.5, 24.5, 62, 12, 0.0, 8.0, 1),
            _demo_day(1, 30.5, 23.5, 80, 65, 15.0, 17.0, 63),
            _demo_day(2, 28.5, 22.5, 87, 85, 28.0, 22.0, 82),
            _demo_day(3, 29.0, 23.0, 82, 68, 16.0, 18.0, 61),
            _demo_day(4, 31.5, 24.0, 68, 25, 1.0, 12.0, 2),
            _demo_day(5, 34.0, 25.5, 56, 8, 0.0, 8.0, 0),
            _demo_day(6, 34.5, 25.5, 54, 5, 0.0, 7.0, 0),
        ],
    },
    "mahasamund": {
        "display_name": "Mahasamund, Chhattisgarh", "latitude": 21.1093, "longitude": 82.0980,
        "days": [
            _demo_day(0, 32.0, 24.0, 70, 20, 0.5, 10.0, 2),
            _demo_day(1, 33.0, 24.5, 63, 10, 0.0, 9.0, 1),
            _demo_day(2, 30.0, 23.5, 79, 58, 10.0, 15.0, 61),
            _demo_day(3, 28.5, 22.5, 86, 80, 24.0, 20.0, 80),
            _demo_day(4, 29.5, 23.0, 81, 66, 14.0, 17.0, 61),
            _demo_day(5, 32.0, 24.0, 68, 22, 1.0, 11.0, 2),
            _demo_day(6, 33.5, 25.0, 60, 10, 0.0, 8.0, 0),
        ],
    },
    "korba": {
        "display_name": "Korba, Chhattisgarh", "latitude": 22.3595, "longitude": 82.7501,
        "days": [
            _demo_day(0, 31.5, 23.5, 72, 25, 1.0, 11.0, 2),
            _demo_day(1, 29.5, 22.5, 82, 62, 13.0, 16.0, 61),
            _demo_day(2, 27.5, 21.5, 89, 84, 26.0, 21.0, 82),
            _demo_day(3, 28.0, 22.0, 85, 75, 19.0, 19.0, 63),
            _demo_day(4, 30.5, 23.0, 74, 38, 4.0, 13.0, 51),
            _demo_day(5, 32.5, 24.0, 64, 15, 0.0, 10.0, 1),
            _demo_day(6, 33.0, 24.5, 60, 10, 0.0, 9.0, 0),
        ],
    },
    "ambikapur": {
        "display_name": "Ambikapur, Chhattisgarh (Surguja)", "latitude": 23.1200, "longitude": 83.1950,
        "days": [
            _demo_day(0, 28.5, 20.0, 68, 15, 0.0, 9.0, 1),
            _demo_day(1, 29.0, 20.5, 65, 10, 0.0, 8.0, 0),
            _demo_day(2, 27.0, 19.5, 78, 55, 9.0, 14.0, 61),
            _demo_day(3, 25.5, 18.5, 86, 80, 22.0, 19.0, 80),
            _demo_day(4, 26.0, 19.0, 82, 70, 17.0, 17.0, 63),
            _demo_day(5, 28.0, 20.0, 70, 28, 1.0, 11.0, 2),
            _demo_day(6, 29.5, 21.0, 62, 12, 0.0, 9.0, 1),
        ],
    },
    "jagdalpur": {
        "display_name": "Jagdalpur, Chhattisgarh (Bastar)", "latitude": 19.0748, "longitude": 82.0198,
        "days": [
            _demo_day(0, 30.5, 22.5, 76, 35, 3.0, 12.0, 2),
            _demo_day(1, 28.5, 21.5, 84, 62, 14.0, 16.0, 61),
            _demo_day(2, 27.0, 21.0, 90, 88, 32.0, 23.0, 82),
            _demo_day(3, 27.5, 21.5, 87, 76, 21.0, 20.0, 63),
            _demo_day(4, 29.0, 22.0, 79, 50, 7.0, 14.0, 61),
            _demo_day(5, 31.0, 23.0, 68, 20, 0.5, 10.0, 1),
            _demo_day(6, 31.5, 23.5, 64, 15, 0.0, 9.0, 1),
        ],
    },
    "bilha": {
        "display_name": "Bilha, Chhattisgarh (Bilaspur district)", "latitude": 22.1500, "longitude": 82.0500,
        "days": [
            _demo_day(0, 33.0, 24.0, 68, 10, 0.0, 9.0, 1),
            _demo_day(1, 34.0, 25.0, 65, 5, 0.0, 8.0, 0),
            _demo_day(2, 32.0, 24.5, 74, 40, 3.0, 12.0, 61),
            _demo_day(3, 29.0, 23.0, 85, 78, 22.0, 18.0, 63),
            _demo_day(4, 28.5, 22.5, 88, 82, 30.0, 21.0, 80),
            _demo_day(5, 30.0, 23.5, 76, 45, 6.0, 14.0, 61),
            _demo_day(6, 32.5, 24.0, 66, 15, 0.5, 10.0, 2),
        ],
    },
    "raipur": {
        "display_name": "Raipur, Chhattisgarh", "latitude": 21.2514, "longitude": 81.6296,
        "days": [
            _demo_day(0, 34.0, 25.0, 60, 8, 0.0, 8.0, 0),
            _demo_day(1, 34.5, 25.5, 58, 5, 0.0, 7.0, 0),
            _demo_day(2, 33.0, 24.5, 66, 20, 0.5, 11.0, 1),
            _demo_day(3, 30.0, 23.5, 80, 62, 13.0, 16.0, 61),
            _demo_day(4, 28.5, 22.5, 87, 83, 27.0, 21.0, 82),
            _demo_day(5, 30.5, 23.5, 75, 40, 4.0, 13.0, 51),
            _demo_day(6, 33.0, 24.5, 62, 12, 0.0, 9.0, 1),
        ],
    },
}


def _normalize_location_key(location_name: Optional[str]) -> Optional[str]:
    if not location_name:
        return None
    return location_name.strip().lower().split(",")[0].strip()


def _get_seeded(location_name: Optional[str]) -> Optional[dict]:
    key = _normalize_location_key(location_name)
    if not key:
        return None
    return _SEEDED_WEATHER.get(key)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def _has_coordinates(latitude, longitude) -> bool:
    # Farmer.latitude/longitude default to 0.0 -- (0, 0) is open ocean, not a
    # real farm, so it is treated as "no coordinates".
    return bool(latitude) and bool(longitude)


def get_weather(latitude: Optional[float], longitude: Optional[float], location_name: Optional[str]) -> dict:
    """
    Resolves weather for a location, preferring LIVE (Open-Meteo), then a
    STALE cached copy (clearly labelled, with its age) if the provider is
    failing, then the deterministic DEMO table, then UNAVAILABLE.
    Never raises for provider problems -- always returns a well-formed dict.
    Coordinates are expected to be validated by the caller (the router
    returns HTTP 422 for out-of-range values); invalid ones are treated as
    absent here rather than sent to the provider.
    """
    loc_out = {"name": location_name, "latitude": latitude, "longitude": longitude}

    if _has_coordinates(latitude, longitude):
        try:
            validate_coordinates(latitude, longitude)
            coords_ok = True
        except ValueError:
            coords_ok = False
    else:
        coords_ok = False

    if coords_ok:
        key = _cache_key(latitude, longitude)
        now = time.time()
        cached = _live_cache.get(key)
        if cached and now - cached[0] < LIVE_CACHE_TTL_SECONDS:
            return _live_payload(cached[1], loc_out, "LIVE", _cache_meta(cached[0], "fresh"))

        with _lock_for(key):
            # Another thread may have filled the cache while we waited.
            cached = _live_cache.get(key)
            if cached and time.time() - cached[0] < LIVE_CACHE_TTL_SECONDS:
                return _live_payload(cached[1], loc_out, "LIVE", _cache_meta(cached[0], "fresh"))

            failure_expires = _failure_cache.get(key)
            rate_limited = False
            if failure_expires and failure_expires > time.time():
                logger.debug("weather_service: skipping live fetch, recent failure cached for %s", key)
            else:
                try:
                    result = _fetch_live(latitude, longitude)
                    _store(key, result)
                    _failure_cache.pop(key, None)
                    return _live_payload(result, loc_out, "LIVE", _cache_meta(_live_cache[key][0], "live"))
                except WeatherRateLimitError as e:
                    rate_limited = True
                    # Respect Retry-After when given (bounded), else the default.
                    wait = min(max(e.retry_after or _FAILURE_CACHE_TTL_SECONDS, 1.0), 15 * 60)
                    _failure_cache[key] = time.time() + wait
                    logger.info("weather_service: provider rate limit for grid %s", key)
                except WeatherAPIError as e:
                    # Rounded grid key only -- never log precise coordinates.
                    logger.info("weather_service: live fetch failed for grid %s: %s", key, e)
                    _failure_cache[key] = time.time() + _FAILURE_CACHE_TTL_SECONDS

            cached = _live_cache.get(key)
            if cached and time.time() - cached[0] <= STALE_MAX_AGE_SECONDS:
                notice = ("The weather provider is rate limiting requests, so this is the last saved forecast."
                          if rate_limited else
                          "Live weather could not be refreshed, so this is the last saved forecast.")
                return _live_payload(cached[1], loc_out, "STALE", _cache_meta(cached[0], "stale"), notice)

    seeded = _get_seeded(location_name)
    if seeded:
        loc_out = {"name": seeded["display_name"], "latitude": seeded["latitude"], "longitude": seeded["longitude"]}
        days = seeded["days"]
        current = {
            "temperature": days[0]["temp_max"],
            "humidity": days[0]["humidity"],
            "precipitation_mm": days[0]["rainfall_mm"],
            "weather_code": days[0]["weather_code"],
            "condition": days[0]["condition"],
            "wind_speed_kmh": days[0]["wind_speed_kmh"],
        }
        return {"status": "DEMO", "source": "CropWise Demo Dataset", "location": loc_out,
                "current": current, "forecast": days, "hourly": [], "cache": None,
                "fetched_at": None, "notice": None, "units": provider.UNITS, "attribution": None}

    return {"status": "UNAVAILABLE", "source": None, "location": loc_out, "current": None,
            "forecast": [], "hourly": [], "cache": None, "fetched_at": None,
            "notice": None, "units": provider.UNITS, "attribution": None}


# ---------------------------------------------------------------------------
# Weather-risk derivation for the recommendation engine (replaces
# simulate_weather_risk's OUTPUT when real/seeded weather is available --
# see app/services/recommendation_engine.py. simulate_weather_risk itself
# is left intact as the final fallback when no weather data exists at all).
#
# DOCUMENTED RULE (deterministic, not an ML model):
#   tomorrow's rainfall_probability >= 70  OR rainfall_mm >= 20  -> High
#   tomorrow's rainfall_probability >= 40  OR rainfall_mm >= 8   -> Medium
#   otherwise                                                     -> Low
# ---------------------------------------------------------------------------

def derive_weather_risk(weather_result: dict):
    forecast = weather_result.get("forecast") or []
    if len(forecast) < 2:
        return None  # not enough data to assess "tomorrow" -- caller falls back
    tomorrow = forecast[1]
    prob = tomorrow.get("rainfall_probability") or 0
    mm = tomorrow.get("rainfall_mm") or 0
    if prob >= 70 or mm >= 20:
        risk = "High"
    elif prob >= 40 or mm >= 8:
        risk = "Medium"
    else:
        risk = "Low"
    source_word = "Live" if weather_result.get("status") in ("LIVE", "STALE") else "Demo"
    note = (
        f"{source_word} forecast: {tomorrow['condition']} tomorrow, "
        f"{int(prob)}% rain chance. "
        + ("This is demonstration data, not a live forecast." if source_word == "Demo" else "")
    ).strip()
    return risk, note
