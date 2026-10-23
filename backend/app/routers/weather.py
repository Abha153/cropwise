"""
Weather endpoints. Thin HTTP layer over app/services/weather_service.py,
app/services/geocoding_service.py and app/services/farm_advisory.py -- all
fetch/fallback/validation/advisory logic lives there, not here.

  GET /weather/farmer            -- auth required, uses the signed-in farmer's
                                    own saved location/coordinates.
  GET /weather                   -- public ad-hoc lookup by lat/lon and/or a
                                    location name. `include_advisory=true`
                                    adds the rule-based farming advisory
                                    (optionally for a `crop` + `growth_stage`).
  GET /weather/geocode/search    -- location autocomplete (name, village,
                                    district, state, PIN code, "lat, lon").
  GET /weather/geocode/reverse   -- coordinates -> readable place name.

Weather and place lookups are not private account data (same precedent as
/market/nearest-market), so they are public. Coordinates are never logged
here, and the services round them before calling or caching with a provider.
"""
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth_utils import require_farmer
from app.services import weather_service, geocoding_service, farm_advisory
from app.services.geocoding_service import GeocodingError

router = APIRouter(prefix="/weather", tags=["weather"])

_GEOCODE_HTTP_STATUS = {"bad_query": 422, "rate_limited": 429, "unavailable": 503, "bad_response": 502}
_GEOCODE_SAFE_MESSAGE = {
    "bad_query": "Enter at least 2 characters, or valid coordinates.",
    "rate_limited": "Location search is busy right now. Please try again in a moment.",
    "unavailable": "Location search is temporarily unavailable.",
    "bad_response": "Location search returned an unexpected response.",
}


def _validated_coordinates(latitude: Optional[float], longitude: Optional[float]):
    """Both-or-neither, in range. Raises HTTP 422 otherwise."""
    if latitude is None and longitude is None:
        return None, None
    if latitude is None or longitude is None:
        raise HTTPException(status_code=422, detail="Provide both latitude and longitude.")
    try:
        return weather_service.validate_coordinates(latitude, longitude)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/farmer")
def farmer_weather(current=Depends(require_farmer)):
    farmer = current
    lat = farmer.latitude if farmer.latitude else None
    lon = farmer.longitude if farmer.longitude else None
    return weather_service.get_weather(lat, lon, farmer.location)


@router.get("")
def weather_lookup(
    latitude: Annotated[Optional[float], Query()] = None,
    longitude: Annotated[Optional[float], Query()] = None,
    location: Annotated[Optional[str], Query(max_length=120)] = None,
    include_advisory: Annotated[bool, Query()] = False,
    crop: Annotated[Optional[str], Query(max_length=40)] = None,
    growth_stage: Annotated[Optional[str], Query(max_length=20)] = None,
):
    latitude, longitude = _validated_coordinates(latitude, longitude)
    result = weather_service.get_weather(latitude, longitude, location)
    if include_advisory:
        result = {**result, "advisory": farm_advisory.build_advisory(result, crop, growth_stage)}
    return result


@router.get("/geocode/search")
def geocode_search(
    q: Annotated[str, Query(min_length=1, max_length=120)],
    count: Annotated[int, Query(ge=1, le=15)] = 8,
    language: Annotated[str, Query(max_length=5)] = "en",
    country_code: Annotated[Optional[str], Query(min_length=2, max_length=2)] = None,
):
    try:
        results = geocoding_service.search_locations(q, count=count, language=language, country_code=country_code)
    except GeocodingError as e:
        raise HTTPException(status_code=_GEOCODE_HTTP_STATUS.get(e.code, 502), detail=_GEOCODE_SAFE_MESSAGE.get(e.code, "Location search failed."))
    return {"query": q.strip(), "results": results}


@router.get("/geocode/reverse")
def geocode_reverse(
    latitude: Annotated[float, Query(ge=-90, le=90)],
    longitude: Annotated[float, Query(ge=-180, le=180)],
    language: Annotated[str, Query(max_length=5)] = "en",
):
    try:
        return geocoding_service.reverse_geocode(latitude, longitude, language=language)
    except GeocodingError as e:
        raise HTTPException(status_code=_GEOCODE_HTTP_STATUS.get(e.code, 502), detail=_GEOCODE_SAFE_MESSAGE.get(e.code, "Place lookup failed."))
