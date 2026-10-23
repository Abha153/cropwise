"""
Location search (forward geocoding) and reverse geocoding for the weather
feature.

PROVIDERS
  * Forward search: Open-Meteo Geocoding API
    (https://open-meteo.com/en/docs/geocoding-api) -- GeoNames-based, no key
    needed on the free tier, covers cities, towns, villages and (where the
    dataset has them) postal codes. Free tier is non-commercial; see
    open_meteo_provider.py for the licensing note.
  * Reverse: OpenStreetMap Nominatim. Its usage policy requires an
    identifying User-Agent and at most 1 request/second, which this module
    enforces (single process-wide throttle) and caches aggressively so that
    repeat lookups never reach Nominatim.

PRIVACY
  Reverse-geocoding coordinates are rounded to 3 decimals (~110 m) before
  they leave this server or enter the cache, and are never logged. A farm
  does not need to be located more precisely than that to name its village.

Both providers sit behind the two public functions below so they can be
replaced without touching the router or the UI.
"""
import math
import re
import threading
import time
from typing import Optional

import httpx

from app.config import settings, logger

REQUEST_TIMEOUT_SECONDS = 5.0
RETRY_BACKOFF_SECONDS = (0.3,)
SEARCH_CACHE_TTL_SECONDS = 60 * 60
REVERSE_CACHE_TTL_SECONDS = 24 * 60 * 60
NOMINATIM_MIN_INTERVAL_SECONDS = 1.0
_CACHE_MAX_ENTRIES = 1000

MIN_QUERY_LENGTH = 2
MAX_QUERY_LENGTH = 100

_COORD_RE = re.compile(r"^\s*(-?\d{1,3}(?:\.\d+)?)\s*[,;\s]\s*(-?\d{1,3}(?:\.\d+)?)\s*$")


class GeocodingError(Exception):
    """Provider failure. `code` is one of: bad_query, rate_limited,
    unavailable, bad_response."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


_search_cache: dict = {}
_reverse_cache: dict = {}
_nominatim_lock = threading.Lock()
_last_nominatim_call = 0.0


def _cache_get(cache: dict, key, ttl: float):
    hit = cache.get(key)
    if hit and time.time() - hit[0] < ttl:
        return hit[1]
    return None


def _cache_put(cache: dict, key, value):
    if len(cache) >= _CACHE_MAX_ENTRIES:
        cache.pop(min(cache, key=lambda k: cache[k][0]), None)
    cache[key] = (time.time(), value)


def parse_coordinates(query: str) -> Optional[tuple]:
    """'22.08, 82.14' / '22.08 82.14' -> (22.08, 82.14) when both are in
    range, else None. Note: a bare 6-digit PIN code never matches."""
    m = _COORD_RE.match(query or "")
    if not m:
        return None
    lat, lon = float(m.group(1)), float(m.group(2))
    if -90 <= lat <= 90 and -180 <= lon <= 180:
        return lat, lon
    return None


def _get_json(url: str, params: dict, headers: Optional[dict] = None):
    attempts = len(RETRY_BACKOFF_SECONDS) + 1
    for attempt in range(attempts):
        try:
            with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS) as client:
                resp = client.get(url, params=params, headers=headers or {})
        except httpx.HTTPError as e:
            err = GeocodingError("unavailable", f"network error: {type(e).__name__}")
        else:
            if resp.status_code == 200:
                try:
                    return resp.json()
                except ValueError as e:
                    raise GeocodingError("bad_response", "invalid JSON from geocoder") from e
            if resp.status_code == 429:
                raise GeocodingError("rate_limited", "geocoder rate limit reached")
            err = GeocodingError("unavailable", f"HTTP {resp.status_code}")
            if resp.status_code < 500:
                raise err
        if attempt < attempts - 1:
            time.sleep(RETRY_BACKOFF_SECONDS[attempt])
    raise err


def _label(name, admin2, admin1, country) -> str:
    parts = []
    for p in (name, admin2, admin1, country):
        if p and p not in parts:
            parts.append(p)
    return ", ".join(parts)


# ---------------------------------------------------------------------------
# Forward search
# ---------------------------------------------------------------------------

def normalize_search_results(data) -> list:
    """Open-Meteo geocoding payload -> list of internal location dicts.
    Entries without usable coordinates are dropped."""
    if not isinstance(data, dict):
        raise GeocodingError("bad_response", "geocoder response is not an object")
    rows = data.get("results")
    if rows is None:
        return []  # Open-Meteo omits "results" entirely when nothing matches
    if not isinstance(rows, list):
        raise GeocodingError("bad_response", "geocoder 'results' is not a list")
    out = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        try:
            lat, lon = float(r["latitude"]), float(r["longitude"])
        except (KeyError, TypeError, ValueError):
            continue
        if not (math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180):
            continue
        name = r.get("name")
        if not name:
            continue
        admin1, admin2, country = r.get("admin1"), r.get("admin2"), r.get("country")
        out.append({
            "id": str(r.get("id") or f"{lat:.4f},{lon:.4f}"),
            "kind": "place",
            "name": name,
            "admin2": admin2,          # district / county
            "admin1": admin1,          # state
            "country": country,
            "country_code": r.get("country_code"),
            "latitude": round(lat, 4),
            "longitude": round(lon, 4),
            "timezone": r.get("timezone"),
            "postcodes": r.get("postcodes") if isinstance(r.get("postcodes"), list) else None,
            "label": _label(name, admin2, admin1, country),
        })
    return out


def search_locations(query: str, count: int = 8, language: str = "en",
                     country_code: Optional[str] = None) -> list:
    """Autocomplete-style location search. Raises GeocodingError. Returns a
    single 'coordinates' entry when the query is a lat,lon pair."""
    q = (query or "").strip()
    if not (MIN_QUERY_LENGTH <= len(q) <= MAX_QUERY_LENGTH) or any(ord(c) < 32 for c in q):
        raise GeocodingError("bad_query", f"query must be {MIN_QUERY_LENGTH}-{MAX_QUERY_LENGTH} printable characters")
    count = max(1, min(int(count), 15))

    coords = parse_coordinates(q)
    if coords:
        lat, lon = coords
        return [{
            "id": f"coords:{lat:.4f},{lon:.4f}", "kind": "coordinates",
            "name": f"{lat:.4f}, {lon:.4f}", "admin2": None, "admin1": None,
            "country": None, "country_code": None,
            "latitude": round(lat, 4), "longitude": round(lon, 4),
            "timezone": None, "postcodes": None,
            "label": f"Coordinates {lat:.4f}, {lon:.4f}",
        }]

    key = (q.lower(), count, language, (country_code or "").upper())
    cached = _cache_get(_search_cache, key, SEARCH_CACHE_TTL_SECONDS)
    if cached is not None:
        return cached

    params = {"name": q, "count": count, "language": language, "format": "json"}
    if country_code:
        params["countryCode"] = country_code.upper()
    api_key = getattr(settings, "open_meteo_api_key", "")
    if api_key:
        params["apikey"] = api_key
    results = normalize_search_results(_get_json(settings.open_meteo_geocoding_url, params))
    _cache_put(_search_cache, key, results)
    return results


# ---------------------------------------------------------------------------
# Reverse geocoding
# ---------------------------------------------------------------------------

def normalize_reverse(data, lat: float, lon: float) -> dict:
    """Nominatim jsonv2 payload -> {name, admin2, admin1, country, label}."""
    if not isinstance(data, dict) or "error" in data:
        raise GeocodingError("unavailable", "no place found for these coordinates")
    addr = data.get("address")
    if not isinstance(addr, dict):
        raise GeocodingError("bad_response", "reverse geocoder returned no address")
    name = next((addr.get(k) for k in ("village", "town", "city", "hamlet", "suburb", "municipality", "county") if addr.get(k)), None)
    if not name:
        raise GeocodingError("unavailable", "no named place at these coordinates")
    admin2 = addr.get("state_district") or addr.get("county")
    if admin2 == name:
        admin2 = None
    admin1 = addr.get("state")
    country = addr.get("country")
    return {
        "name": name, "admin2": admin2, "admin1": admin1, "country": country,
        "latitude": lat, "longitude": lon,
        "label": _label(name, admin2, admin1, country),
    }


def reverse_geocode(latitude: float, longitude: float, language: str = "en") -> dict:
    """Coordinates -> readable place. Raises GeocodingError (the caller shows
    the rounded coordinates instead -- it never invents a place name)."""
    lat, lon = round(float(latitude), 3), round(float(longitude), 3)
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise GeocodingError("bad_query", "coordinates out of range")
    key = (lat, lon, language)
    cached = _cache_get(_reverse_cache, key, REVERSE_CACHE_TTL_SECONDS)
    if cached is not None:
        return cached

    global _last_nominatim_call
    with _nominatim_lock:  # serialises calls so the 1 req/s policy holds
        wait = NOMINATIM_MIN_INTERVAL_SECONDS - (time.time() - _last_nominatim_call)
        if wait > 0:
            time.sleep(wait)
        try:
            data = _get_json(
                settings.nominatim_base_url.rstrip("/") + "/reverse",
                {"format": "jsonv2", "lat": lat, "lon": lon, "zoom": 12,
                 "addressdetails": 1, "accept-language": language},
                headers={"User-Agent": settings.geocoder_user_agent},
            )
        finally:
            _last_nominatim_call = time.time()
    result = normalize_reverse(data, lat, lon)
    _cache_put(_reverse_cache, key, result)
    return result
