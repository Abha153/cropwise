"""Shared builders for Open-Meteo-shaped payloads used by the weather tests.
Shapes follow the documented Forecast API response (timezone=auto, 7 days,
hourly 168 rows). Values are synthetic test data, never production data."""
import copy
import datetime as dt

NOW_LOCAL = "2026-10-19T14:30"   # "current.time" -- in the location's own timezone


def open_meteo_payload(days=7, overrides=None, hourly=True, now=NOW_LOCAL):
    start = dt.date(2026, 10, 19)
    dates = [(start + dt.timedelta(days=i)).isoformat() for i in range(days)]
    payload = {
        "latitude": 22.08, "longitude": 82.14, "timezone": "Asia/Kolkata",
        "timezone_abbreviation": "GMT+5:30", "utc_offset_seconds": 19800,
        "current": {
            "time": now, "interval": 900, "temperature_2m": 31.2, "apparent_temperature": 34.0,
            "relative_humidity_2m": 64, "is_day": 1, "precipitation": 0.0, "rain": 0.0,
            "weather_code": 1, "cloud_cover": 20, "pressure_msl": 1008.4,
            "wind_speed_10m": 11.4, "wind_direction_10m": 250, "wind_gusts_10m": 22.0,
        },
        "daily": {
            "time": dates,
            "weather_code": [1, 61, 2, 0, 63, 2, 1][:days],
            "temperature_2m_max": [33.1, 29.5, 32.0, 34.2, 28.0, 31.5, 32.8][:days],
            "temperature_2m_min": [24.0, 22.5, 23.8, 25.1, 22.0, 23.5, 24.2][:days],
            "precipitation_probability_max": [10, 65, 20, 5, 78, 25, 15][:days],
            "precipitation_sum": [0.0, 12.0, 1.0, 0.0, 24.0, 2.0, 0.5][:days],
            "wind_speed_10m_max": [10.0, 15.0, 11.0, 9.0, 19.0, 12.0, 10.5][:days],
            "wind_gusts_10m_max": [22.0, 30.0, 24.0, 20.0, 38.0, 26.0, 23.0][:days],
            "sunrise": [f"{d}T06:05" for d in dates],
            "sunset": [f"{d}T17:40" for d in dates],
            "et0_fao_evapotranspiration": [4.5, 3.2, 4.1, 4.8, 2.9, 4.0, 4.4][:days],
        },
    }
    if hourly:
        times, rows = [], {k: [] for k in (
            "temperature_2m", "apparent_temperature", "relative_humidity_2m",
            "precipitation_probability", "precipitation", "weather_code",
            "wind_speed_10m", "wind_gusts_10m", "et0_fao_evapotranspiration")}
        for d in range(days):
            for h in range(24):
                times.append(f"{dates[d]}T{h:02d}:00")
                rows["temperature_2m"].append(24 + h * 0.3)
                rows["apparent_temperature"].append(25 + h * 0.3)
                rows["relative_humidity_2m"].append(60)
                rows["precipitation_probability"].append(10)
                rows["precipitation"].append(0.0)
                rows["weather_code"].append(1)
                rows["wind_speed_10m"].append(8.0)
                rows["wind_gusts_10m"].append(15.0)
                rows["et0_fao_evapotranspiration"].append(0.2)
        payload["hourly"] = {"time": times, **rows}
    for path, value in (overrides or {}).items():
        node = payload
        keys = path.split(".")
        for k in keys[:-1]:
            node = node[k]
        if value is _DELETE:
            node.pop(keys[-1], None)
        else:
            node[keys[-1]] = value
    return copy.deepcopy(payload)


_DELETE = object()
DELETE = _DELETE
