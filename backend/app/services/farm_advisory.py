"""
Agricultural weather advisory engine.

PURE module: no HTTP, database or framework imports. It takes the normalized
weather dict produced by weather_service.get_weather() and returns advisory
data, so every rule can be unit tested (tests/test_farm_advisory.py) and
improved independently of the UI.

WHAT THIS IS -- AND IS NOT
  * Rule-based guidance computed from a weather FORECAST. It does not know
    the soil, irrigation, variety, sowing date, pests or disease pressure,
    and never claims anything about yield, crop health or soil moisture.
  * It is NOT an India Meteorological Department (IMD) warning. IMD's
    rainfall classes are used only as a vocabulary for forecast amounts, and
    IMD's heat/cold-wave warnings need departure-from-normal data we don't
    have, so the words "heat wave"/"cold wave" are never used.
  * Every insight states the numbers that triggered it (`trigger`) and the
    rule it rests on (`basis`). Thresholds marked "heuristic" are
    conservative general-purpose rules, not agronomic standards.

THRESHOLD SOURCES
  * Rainfall amounts per 24 h (IMD classification): light 2.5-15.5 mm,
    moderate 15.6-64.4 mm, heavy 64.5-115.5 mm, very heavy 115.6-204.4 mm,
    extremely heavy >= 204.5 mm.
  * Crop coefficients (Kc): FAO Irrigation & Drainage Paper 56, Table 12
    (single-coefficient values). ETc = Kc x ET0.
  * Crop-specific heat thresholds: widely published agronomy guidance for
    heat-sensitive reproductive stages; indicative only -- confirm with your
    local KVK / state agriculture university.
  * Spray conditions: common label/extension guidance (low wind, no rain
    shortly after, avoid hot hours); the product label always overrides.
"""
import datetime as dt
from typing import Optional

LEVEL_ORDER = {"high": 3, "moderate": 2, "info": 1, "low": 0}

# ---- IMD 24 h rainfall classes (mm) ---------------------------------------
IMD_LIGHT_MIN = 2.5
IMD_MODERATE_MIN = 15.6
IMD_HEAVY_MIN = 64.5
IMD_VERY_HEAVY_MIN = 115.6
IMD_EXTREME_MIN = 204.5

# ---- General (crop-agnostic) thresholds ------------------------------------
HEAT_MODERATE_C = 35.0   # heuristic: sustained >=35 C stresses most field crops
HEAT_HIGH_C = 40.0
COLD_MODERATE_C = 5.0    # heuristic: chilling risk for tender crops
COLD_HIGH_C = 2.0        # frost becomes possible near/below ~2 C air temperature
WIND_MODERATE_KMH = 40.0  # Beaufort 6 "strong breeze" starts ~39 km/h
WIND_HIGH_KMH = 60.0
CUMULATIVE_RAIN_3D_MODERATE_MM = IMD_HEAVY_MIN  # heuristic waterlogging concern

# ---- Spraying / field-work rules ------------------------------------------
SPRAY_MAX_WIND_KMH = 15.0
SPRAY_MAX_GUST_KMH = 25.0
SPRAY_MAX_RAIN_PROB = 20.0
SPRAY_MAX_TEMP_C = 32.0
SPRAY_LOOKAHEAD_MAX_PROB = 30.0
SPRAY_MIN_WINDOW_HOURS = 2
DRY_DAY_MAX_MM = IMD_LIGHT_MIN - 0.01   # < 2.5 mm
DRY_DAY_MAX_PROB = 40.0
HARVEST_MIN_DRY_DAYS = 2

# ---- ET0 interpretation (mm/day) -------------------------------------------
ET0_LOW_MAX = 3.0
ET0_MODERATE_MAX = 5.0

GROWTH_STAGES = {
    "initial": "Initial / sowing",
    "development": "Development / vegetative",
    "mid": "Mid-season (flowering, grain or fruit set)",
    "late": "Late season / maturity",
}

# FAO-56 Table 12 single Kc values (initial / mid / end). heat_c: crop-specific
# heat-stress air temperature for the mid-season (reproductive) stage, only
# where widely documented; None = use the general rule.
CROP_PROFILES = {
    "wheat": {"label": "Wheat", "kc": (0.30, 1.15, 0.25), "heat_c": 35.0},
    "paddy": {"label": "Paddy (Rice)", "kc": (1.05, 1.20, 0.90), "heat_c": 35.0},
    "maize": {"label": "Maize", "kc": (0.30, 1.20, 0.35), "heat_c": 35.0},
    "tomato": {"label": "Tomato", "kc": (0.60, 1.15, 0.80), "heat_c": 35.0},
    "potato": {"label": "Potato", "kc": (0.50, 1.15, 0.75), "heat_c": None},
    "onion": {"label": "Onion", "kc": (0.70, 1.05, 0.75), "heat_c": None},
    "soybean": {"label": "Soybean", "kc": (0.40, 1.15, 0.50), "heat_c": None},
    "groundnut": {"label": "Groundnut", "kc": (0.40, 1.15, 0.60), "heat_c": None},
    "mustard": {"label": "Mustard", "kc": (0.35, 1.15, 0.35), "heat_c": None},
    "chickpea": {"label": "Chickpea (Chana)", "kc": (0.40, 1.00, 0.35), "heat_c": None},
    "sugarcane": {"label": "Sugarcane", "kc": (0.40, 1.25, 0.75), "heat_c": None},
}

_CROP_ALIASES = {
    "paddy": "paddy", "rice": "paddy", "paddy (rice)": "paddy", "paddy rice": "paddy",
    "gram": "chickpea", "chana": "chickpea", "chana (gram)": "chickpea",
    "chana gram": "chickpea", "chickpea": "chickpea", "bengal gram": "chickpea",
    "rapeseed": "mustard", "mustard": "mustard",
    "corn": "maize", "maize": "maize", "wheat": "wheat", "tomato": "tomato",
    "potato": "potato", "onion": "onion", "soybean": "soybean", "soya": "soybean",
    "groundnut": "groundnut", "peanut": "groundnut", "sugarcane": "sugarcane",
}


def supported_crops() -> list:
    return [{"key": k, "label": v["label"]} for k, v in CROP_PROFILES.items()]


def resolve_crop(crop: Optional[str]) -> Optional[str]:
    if not crop:
        return None
    return _CROP_ALIASES.get(crop.strip().lower())


def kc_for(crop_key: str, stage: str) -> Optional[float]:
    """FAO-56 single Kc for the stage. 'development' is the midpoint between
    the initial and mid values (FAO-56 interpolates over the stage; a
    midpoint is a coarse approximation and is labelled as such)."""
    profile = CROP_PROFILES.get(crop_key)
    if not profile or stage not in GROWTH_STAGES:
        return None
    ini, mid, end = profile["kc"]
    development = round((ini + mid) / 2 + 1e-9, 2)  # +1e-9: round half-up, not float-banker's
    return {"initial": ini, "development": development, "mid": mid, "late": end}[stage]


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def classify_rain_24h(mm: Optional[float]) -> str:
    if mm is None:
        return "unknown"
    if mm < 0.1:
        return "none"
    if mm < IMD_LIGHT_MIN:
        return "very light"
    if mm < IMD_MODERATE_MIN:
        return "light"
    if mm < IMD_HEAVY_MIN:
        return "moderate"
    if mm < IMD_VERY_HEAVY_MIN:
        return "heavy"
    if mm < IMD_EXTREME_MIN:
        return "very heavy"
    return "extremely heavy"


def _day_label(iso: str) -> str:
    try:
        return dt.date.fromisoformat(iso).strftime("%a %d %b")
    except (TypeError, ValueError):
        return str(iso)


def _hour_label(ts: str) -> str:
    try:
        return dt.datetime.fromisoformat(ts).strftime("%a %H:%M")
    except (TypeError, ValueError):
        return str(ts)


def _vals(rows, key):
    return [r[key] for r in rows if r.get(key) is not None]


def _insight(id_, category, level, title, message, trigger, basis, **extra):
    return {"id": id_, "category": category, "level": level, "title": title,
            "message": message, "trigger": trigger, "basis": basis, **extra}


# ---------------------------------------------------------------------------
# Risk rules (each returns one insight)
# ---------------------------------------------------------------------------

def _heat(days, crop_key, stage):
    tmax = max(_vals(days, "temp_max"), default=None)
    if tmax is None:
        return None
    hot_day = max((d for d in days if d.get("temp_max") is not None), key=lambda d: d["temp_max"])
    when = _day_label(hot_day["date"])
    profile = CROP_PROFILES.get(crop_key) if crop_key else None
    crop_threshold = profile["heat_c"] if profile and stage == "mid" else None

    if crop_threshold is not None:
        level = "high" if tmax >= crop_threshold + 3 else "moderate" if tmax >= crop_threshold else "low"
        basis = (f"Indicative heat-stress threshold for {profile['label']} at the mid-season "
                 f"(flowering / grain or fruit set) stage: about {crop_threshold:.0f}°C. Confirm locally.")
        if level == "low":
            msg = f"Forecast highs stay below about {crop_threshold:.0f}°C for {profile['label']} at this stage."
        else:
            msg = (f"Highs of {tmax:.0f}°C are forecast on {when}, at or above the level where {profile['label']} "
                   "can suffer heat stress at this stage. Ask your local agriculture office about suitable precautions "
                   "(for example, irrigation timing).")
    else:
        level = "high" if tmax >= HEAT_HIGH_C else "moderate" if tmax >= HEAT_MODERATE_C else "low"
        basis = ("General heuristic: highs of 35°C or more can stress many field crops, 40°C or more is severe. "
                 "Crop-specific limits are only applied for wheat, paddy, maize and tomato at mid-season.")
        if level == "low":
            msg = "No heat-stress level temperatures in the forecast."
        else:
            msg = (f"Highs of {tmax:.0f}°C are forecast on {when}. Heat can stress crops, especially during flowering "
                   "and fruit or grain set. Choose a crop and stage for more specific guidance.")
    return _insight("heat", "temperature", level, "Heat stress", msg,
                    f"Highest forecast temperature: {tmax:.0f}°C on {when}.", basis, when=when)


def _cold(days):
    tmin = min(_vals(days, "temp_min"), default=None)
    if tmin is None:
        return None
    cold_day = min((d for d in days if d.get("temp_min") is not None), key=lambda d: d["temp_min"])
    when = _day_label(cold_day["date"])
    level = "high" if tmin <= COLD_HIGH_C else "moderate" if tmin <= COLD_MODERATE_C else "low"
    msg = {
        "low": "No cold-stress level temperatures in the forecast.",
        "moderate": f"Lows of {tmin:.0f}°C are forecast on {when}. Tender crops and seedlings can be chilled at this level.",
        "high": f"Lows of {tmin:.0f}°C are forecast on {when}. Frost is possible near the ground at this air temperature; protect tender crops and seedlings if you can.",
    }[level]
    return _insight("cold", "temperature", level, "Cold stress", msg,
                    f"Lowest forecast temperature: {tmin:.0f}°C on {when}.",
                    "General heuristic: air temperature of 5°C or below can chill tender crops, 2°C or below makes ground frost possible.",
                    when=when)


def _wind(days, hourly):
    gusts = _vals(days, "wind_gusts_kmh")
    speeds = _vals(days, "wind_speed_kmh")
    if not speeds and not gusts:
        return None
    peak_speed = max(speeds, default=0.0)
    peak_gust = max(gusts, default=None)
    ref = peak_gust if peak_gust is not None else peak_speed
    level = "high" if ref >= WIND_HIGH_KMH else "moderate" if ref >= WIND_MODERATE_KMH else "low"
    key = "wind_gusts_kmh" if peak_gust is not None else "wind_speed_kmh"
    day = max((d for d in days if d.get(key) is not None), key=lambda d: d[key])
    when = _day_label(day["date"])
    kind = "gusts" if peak_gust is not None else "winds"
    msg = {
        "low": "No strong winds in the forecast.",
        "moderate": f"Strong {kind} up to {ref:.0f} km/h on {when}. Tall or staked crops may lodge, and spraying is not advisable.",
        "high": f"Very strong {kind} up to {ref:.0f} km/h on {when}. Secure structures, nets and staking, and avoid field spraying.",
    }[level]
    return _insight("wind", "wind", level, "High wind", msg,
                    f"Peak forecast {kind}: {ref:.0f} km/h on {when}.",
                    "General heuristic: 40 km/h or more is a strong breeze, 60 km/h or more is damaging for many crops and structures.",
                    when=when)


def _rain_risk(days):
    rain = [(d, d["rainfall_mm"]) for d in days if d.get("rainfall_mm") is not None]
    if not rain:
        return None
    worst_day, worst = max(rain, key=lambda x: x[1])
    when = _day_label(worst_day["date"])
    three_day = sum(mm for _, mm in rain[:3])
    cls = classify_rain_24h(worst)
    if worst >= IMD_HEAVY_MIN:
        level = "high"
    elif three_day >= CUMULATIVE_RAIN_3D_MODERATE_MM:
        level = "moderate"
    else:
        level = "low"
    if level == "low":
        msg = "No heavy rainfall is forecast in the next 7 days."
    elif level == "high":
        msg = (f"{cls.capitalize()} rain ({worst:.0f} mm) is forecast on {when}. Check field drainage and "
               "low-lying plots for waterlogging, and plan harvesting and transport around it.")
    else:
        msg = (f"About {three_day:.0f} mm of rain is forecast over the next 3 days. Check drainage in "
               "low-lying fields. Actual waterlogging depends on your soil and field slope.")
    return _insight("heavy_rain", "rainfall", level, "Heavy rain and waterlogging", msg,
                    f"Largest 24 h forecast: {worst:.0f} mm ({cls}) on {when}; next 3 days total: {three_day:.0f} mm.",
                    "Daily amounts use the IMD rainfall classes (heavy = 64.5 mm or more in 24 h). The 3-day total of 64.5 mm is a heuristic. Soil type and drainage are not considered.",
                    when=when)


# ---------------------------------------------------------------------------
# Rainfall outlook, ET0, ETc
# ---------------------------------------------------------------------------

def _rain_outlook(days):
    with_rain = [d for d in days if d.get("rainfall_mm") is not None]
    if not with_rain:
        return None
    total = sum(d["rainfall_mm"] for d in with_rain)
    next3 = sum(d["rainfall_mm"] for d in with_rain[:3])
    rainy = [d for d in with_rain if d["rainfall_mm"] >= IMD_LIGHT_MIN]
    if rainy:
        first = rainy[0]
        msg = (f"Rain of {first['rainfall_mm']:.0f} mm is forecast on {_day_label(first['date'])} "
               f"({total:.0f} mm over {len(with_rain)} days). Review your irrigation needs against this before "
               "irrigating; the forecast alone is not a reason to cancel.")
    else:
        msg = (f"Very little rain is forecast ({total:.1f} mm over {len(with_rain)} days). "
               "Plan irrigation according to your crop's needs and soil moisture.")
    return _insight("rain_outlook", "rainfall", "info", "Rainfall outlook for irrigation planning", msg,
                    f"Forecast rain: {next3:.0f} mm in 3 days, {total:.0f} mm in {len(with_rain)} days.",
                    "Sum of daily forecast precipitation. Rain forecasts can shift in timing and amount, especially beyond 3 days.")


def _et0(days):
    et = [d for d in days if d.get("et0_mm") is not None]
    if not et:
        return None, None
    avg = sum(d["et0_mm"] for d in et) / len(et)
    total = sum(d["et0_mm"] for d in et)
    band = "low" if avg < ET0_LOW_MAX else "moderate" if avg <= ET0_MODERATE_MAX else "high"
    rain_total = sum(d["rainfall_mm"] for d in days[:len(et)] if d.get("rainfall_mm") is not None)
    balance = rain_total - total
    msg = (f"Reference evapotranspiration (ET₀) averages {avg:.1f} mm/day, which is {band} atmospheric water demand. "
           f"Forecast rain minus ET₀ over {len(et)} days is {balance:+.0f} mm. ET₀ is the demand of a standard reference grass surface, "
           "not your crop's actual water use, and it says nothing about soil moisture.")
    insight = _insight("et0", "water", "info", "Evaporative demand (ET₀)", msg,
                       f"ET₀ {avg:.1f} mm/day average, {total:.0f} mm total over {len(et)} days; forecast rain {rain_total:.0f} mm.",
                       "FAO-56 reference evapotranspiration from the weather model. Bands: under 3 mm/day low, 3-5 moderate, over 5 high (approximate, typical of warm climates).")
    return insight, {"avg_mm_per_day": round(avg, 2), "total_mm": round(total, 1), "days": len(et),
                     "band": band, "forecast_rain_mm": round(rain_total, 1), "rain_minus_et0_mm": round(balance, 1)}


def _etc(days, crop_key, stage):
    """Crop water demand estimate ETc = Kc x ET0 -- only when both a known
    crop and a growth stage were given."""
    if not crop_key or not stage:
        return None
    kc = kc_for(crop_key, stage)
    et = [d for d in days if d.get("et0_mm") is not None]
    if kc is None or not et:
        return None
    total = sum(d["et0_mm"] for d in et) * kc
    rain = sum(d["rainfall_mm"] for d in days[:len(et)] if d.get("rainfall_mm") is not None)
    label = CROP_PROFILES[crop_key]["label"]
    assumptions = [
        "ETc = Kc x ET₀ using FAO-56 single crop coefficients under standard, well-watered conditions.",
        "Growth stage was chosen by you; the stage can differ between fields." + (
            " 'Development' uses the midpoint of the initial and mid Kc values." if stage == "development" else ""),
        "Soil water, irrigation already applied, rainfall effectiveness and local adjustments are not included.",
    ]
    return {
        "crop": label, "stage": stage, "kc": kc, "days": len(et),
        "etc_mm": round(total, 1), "forecast_rain_mm": round(rain, 1),
        "label": f"Estimated crop water demand for {label} ({GROWTH_STAGES[stage].split(' (')[0].lower()}): "
                 f"about {total:.0f} mm over {len(et)} days (Kc {kc}). This is an estimate, not a measurement.",
        "assumptions": assumptions,
    }


# ---------------------------------------------------------------------------
# Activity windows
# ---------------------------------------------------------------------------

def spraying_windows(hourly) -> dict:
    """Contiguous daytime runs of hours that meet all spray conditions."""
    future = [h for h in hourly if h.get("phase") in ("current", "future")]
    if not future:
        return {"available": False, "windows": [], "reason": "Hourly forecast not available."}

    def ok(i):
        h = future[i]
        if h.get("is_day") is False:
            return False
        wind, gust, prob, mm, temp = (h.get(k) for k in ("wind_speed_kmh", "wind_gusts_kmh", "rain_probability", "rainfall_mm", "temperature"))
        if wind is None or prob is None or mm is None:
            return False  # missing data never counts as "suitable"
        if wind > SPRAY_MAX_WIND_KMH or (gust is not None and gust > SPRAY_MAX_GUST_KMH):
            return False
        if prob > SPRAY_MAX_RAIN_PROB or mm > 0.0:
            return False
        if temp is not None and temp > SPRAY_MAX_TEMP_C:
            return False
        # Rain shortly after would wash the product off.
        for j in (i + 1, i + 2):
            if j < len(future):
                nxt = future[j]
                if (nxt.get("rain_probability") or 0) > SPRAY_LOOKAHEAD_MAX_PROB or (nxt.get("rainfall_mm") or 0) > 0.0:
                    return False
        return True

    windows, run = [], []
    for i in range(len(future)):
        if ok(i):
            run.append(future[i])
        else:
            if len(run) >= SPRAY_MIN_WINDOW_HOURS:
                windows.append(run)
            run = []
    if len(run) >= SPRAY_MIN_WINDOW_HOURS:
        windows.append(run)

    out = []
    for w in windows[:3]:
        end_dt = dt.datetime.fromisoformat(w[-1]["time"]) + dt.timedelta(hours=1)
        out.append({
            "start": w[0]["time"], "end": end_dt.isoformat(timespec="minutes"),
            "label": f"{_hour_label(w[0]['time'])} to {end_dt.strftime('%H:%M')}",
            "hours": len(w),
            "max_wind_kmh": max(_vals(w, "wind_speed_kmh"), default=None),
            "max_rain_probability": max(_vals(w, "rain_probability"), default=None),
        })
    return {"available": True, "windows": out, "hours_checked": len(future)}


def dry_day_runs(days) -> list:
    """Runs of consecutive days with little forecast rain and no strong wind."""
    runs, run = [], []
    for d in days:
        mm, prob = d.get("rainfall_mm"), d.get("rainfall_probability")
        wind = d.get("wind_gusts_kmh") if d.get("wind_gusts_kmh") is not None else d.get("wind_speed_kmh")
        good = (mm is not None and prob is not None and mm <= DRY_DAY_MAX_MM and prob <= DRY_DAY_MAX_PROB
                and (wind is None or wind < WIND_MODERATE_KMH))
        if good:
            run.append(d)
        else:
            if run:
                runs.append(run)
            run = []
    if run:
        runs.append(run)
    return runs


def _harvest_window(days):
    runs = [r for r in dry_day_runs(days) if len(r) >= HARVEST_MIN_DRY_DAYS]
    if not runs:
        return _insight("harvest_window", "activity", "info", "Harvesting and drying window",
                        f"No dry spell of {HARVEST_MIN_DRY_DAYS} or more days is forecast in the next 7 days.",
                        "Looked for consecutive days with under 2.5 mm rain, 40% or lower rain chance and no strong wind.",
                        "Heuristic dry-day rule. Crop maturity and moisture content decide the actual harvest time.")
    best = max(runs, key=len)
    span = f"{_day_label(best[0]['date'])} to {_day_label(best[-1]['date'])}"
    return _insight("harvest_window", "activity", "info", "Harvesting and drying window",
                    f"A dry spell of {len(best)} days is forecast ({span}), which suits harvesting and drying if your crop is mature.",
                    f"{len(best)} consecutive days with under 2.5 mm rain, 40% or lower rain chance and no strong wind.",
                    "Heuristic dry-day rule. Crop maturity and moisture content decide the actual harvest time.",
                    window={"start": best[0]["date"], "end": best[-1]["date"], "days": len(best)})


def _sowing_window(days, crop_key):
    ok_days = [d for d in days
               if d.get("rainfall_mm") is not None and d.get("rainfall_probability") is not None
               and d["rainfall_mm"] < IMD_MODERATE_MIN and d["rainfall_probability"] < 70
               and (d.get("wind_gusts_kmh") or d.get("wind_speed_kmh") or 0) < WIND_MODERATE_KMH]
    caveat = ("Sowing suitability also depends on soil moisture, your crop calendar and variety, none of which "
              "this forecast knows.")
    if not ok_days:
        return _insight("sowing_window", "activity", "info", "Sowing and field work",
                        "Every day in the next 7 days has heavy rain or strong wind forecast. " + caveat,
                        "No day met: under 15.6 mm rain, rain chance under 70%, no strong wind.",
                        "Heuristic: avoid days with moderate-to-heavy rain or strong wind for field operations.")
    labels = ", ".join(_day_label(d["date"]) for d in ok_days)
    return _insight("sowing_window", "activity", "info", "Sowing and field work",
                    f"Days without heavy rain or strong wind: {labels}. " + caveat,
                    f"{len(ok_days)} of {len(days)} days have under 15.6 mm rain, rain chance under 70% and no strong wind.",
                    "Heuristic: avoid days with moderate-to-heavy rain or strong wind for field operations. Not crop-specific.",
                    window={"days": [d["date"] for d in ok_days]})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def build_advisory(weather: dict, crop: Optional[str] = None, growth_stage: Optional[str] = None) -> dict:
    """Returns {available, summary, insights, activities, et0, etc, limitations,
    crop, growth_stage, supported_crops, growth_stages}. Never raises on
    sparse data: rules whose inputs are missing are simply omitted."""
    base = {"supported_crops": supported_crops(),
            "growth_stages": [{"key": k, "label": v} for k, v in GROWTH_STAGES.items()]}
    days = (weather or {}).get("forecast") or []
    if not weather or weather.get("status") == "UNAVAILABLE" or not days:
        return {**base, "available": False, "reason": "No forecast data is available for this location.",
                "summary": None, "insights": [], "activities": {}, "et0": None, "etc": None,
                "limitations": [], "crop": None, "growth_stage": None}

    crop_key = resolve_crop(crop)
    stage = growth_stage if growth_stage in GROWTH_STAGES else None
    hourly = weather.get("hourly") or []

    limitations = [
        "Guidance is computed from a weather forecast. It does not know your soil, irrigation, variety, pests or sowing date, and it cannot predict crop health, disease or yield.",
        "This is not an India Meteorological Department warning. For official alerts, check IMD or your state agriculture department.",
    ]
    status = weather.get("status")
    if status == "DEMO":
        limitations.insert(0, "This advice is based on demonstration data, not a live forecast.")
    elif status == "STALE":
        age = (weather.get("cache") or {}).get("age_seconds")
        mins = f" (about {int(age // 60)} minutes old)" if isinstance(age, (int, float)) else ""
        limitations.insert(0, f"This advice is based on a saved forecast{mins} because live data could not be refreshed.")
    if crop and not crop_key:
        limitations.append(f"'{crop}' has no crop-specific rules yet, so general weather guidance is shown.")
    elif not crop_key:
        limitations.append("No crop selected: general weather guidance only. Choose a crop and growth stage for crop-specific thresholds and a water demand estimate.")
    elif not stage:
        limitations.append("No growth stage selected: crop-specific heat limits and the water demand estimate need one.")
    if not hourly:
        limitations.append("Hourly data is unavailable, so spraying windows cannot be assessed.")
    if not any(d.get("et0_mm") is not None for d in days):
        limitations.append("Evapotranspiration data is unavailable for this response.")

    insights = [i for i in (
        _heat(days, crop_key, stage), _cold(days), _wind(days, hourly), _rain_risk(days),
    ) if i]
    outlook = _rain_outlook(days)
    et0_insight, et0_summary = _et0(days)
    activities = {}

    spray = spraying_windows(hourly) if hourly else {"available": False, "windows": [], "reason": "Hourly forecast not available."}
    if spray["available"]:
        if spray["windows"]:
            w = spray["windows"][0]
            msg = (f"Conditions are suitable for spraying around {w['label']} (wind up to {w['max_wind_kmh']:.0f} km/h, "
                   f"rain chance up to {w['max_rain_probability']:.0f}%). Always follow the product label and local agricultural guidance.")
            level_trigger = f"{len(spray['windows'])} window(s) of {SPRAY_MIN_WINDOW_HOURS}+ hours found in the next {spray['hours_checked']} hours."
        else:
            msg = ("No suitable spraying window in the next 48 hours: wind, rain or heat is outside the usual limits for "
                   "spraying. Follow the product label and local agricultural guidance.")
            level_trigger = f"No run of {SPRAY_MIN_WINDOW_HOURS}+ hours met all conditions in {spray['hours_checked']} hours."
        activities["spraying"] = _insight(
            "spray_window", "activity", "info", "Spraying window", msg, level_trigger,
            "Heuristic from common extension guidance: daytime, wind up to 15 km/h (gusts up to 25), rain chance up to 20% and no rain for the next 2 hours, up to 32°C. The product label overrides this.",
            windows=spray["windows"])
    activities["harvesting"] = _harvest_window(days)
    activities["sowing"] = _sowing_window(days, crop_key)

    etc = _etc(days, crop_key, stage)

    all_items = insights + ([outlook] if outlook else []) + ([et0_insight] if et0_insight else [])
    flagged = sorted((i for i in insights if i["level"] in ("high", "moderate")),
                     key=lambda i: -LEVEL_ORDER[i["level"]])
    if flagged:
        summary = " ".join(f"{i['title']}: {i['message']}" for i in flagged[:2])
    else:
        summary = "No weather risks stand out in the next 7 days."
        if outlook:
            summary += " " + outlook["message"]

    return {**base, "available": True, "summary": summary, "insights": all_items,
            "activities": activities, "et0": et0_summary, "etc": etc, "limitations": limitations,
            "crop": CROP_PROFILES[crop_key]["label"] if crop_key else None, "growth_stage": stage}
