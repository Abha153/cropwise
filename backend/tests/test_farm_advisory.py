"""Advisory engine rules, threshold boundaries and honesty guarantees.
Pure-logic tests: no network, no framework."""
import copy
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from tests.weather_fixtures import open_meteo_payload
from app.services import open_meteo_provider as p
from app.services import farm_advisory as fa


def weather(status="LIVE", days=None, hourly_edit=None, **day_overrides):
    model = p.normalize_forecast(open_meteo_payload())
    w = {"status": status, **copy.deepcopy(model)}
    for i, d in enumerate(w["forecast"]):
        for k, v in day_overrides.items():
            d[k] = v[i] if isinstance(v, list) else v
    if days is not None:
        w["forecast"] = w["forecast"][:days]
    if hourly_edit:
        hourly_edit(w["hourly"])
    return w


def insight(adv, id_):
    return next(i for i in adv["insights"] if i["id"] == id_)


# ---- IMD classes ---------------------------------------------------------

@pytest.mark.parametrize("mm,cls", [
    (None, "unknown"), (0, "none"), (0.09, "none"), (0.1, "very light"), (2.49, "very light"),
    (2.5, "light"), (15.5, "light"), (15.6, "moderate"), (64.4, "moderate"),
    (64.5, "heavy"), (115.5, "heavy"), (115.6, "very heavy"), (204.4, "very heavy"), (204.5, "extremely heavy"),
])
def test_imd_rain_classes(mm, cls):
    assert fa.classify_rain_24h(mm) == cls


# ---- heat / cold (general) -------------------------------------------------

@pytest.mark.parametrize("tmax,level", [(34.9, "low"), (35.0, "moderate"), (39.9, "moderate"), (40.0, "high")])
def test_general_heat_boundaries(tmax, level):
    adv = fa.build_advisory(weather(temp_max=[tmax] + [30.0] * 6))
    assert insight(adv, "heat")["level"] == level


@pytest.mark.parametrize("tmin,level", [(5.1, "low"), (5.0, "moderate"), (2.1, "moderate"), (2.0, "high"), (-1.0, "high")])
def test_cold_boundaries(tmin, level):
    adv = fa.build_advisory(weather(temp_min=[tmin] + [20.0] * 6))
    assert insight(adv, "cold")["level"] == level


def test_never_uses_the_phrase_heat_wave_or_cold_wave_or_claims_imd_warning():
    adv = fa.build_advisory(weather(temp_max=[45.0] * 7, temp_min=[-3.0] * 7))
    text = " ".join(i["message"] + i["title"] for i in adv["insights"]).lower()
    assert "heat wave" not in text and "cold wave" not in text
    assert any("not an india meteorological department warning" in l.lower() for l in adv["limitations"])


# ---- crop-specific heat ----------------------------------------------------

def test_wheat_at_mid_stage_uses_crop_threshold_and_says_so():
    hot = dict(temp_max=[36.0] + [30.0] * 6)
    general = fa.build_advisory(weather(**hot))
    wheat = fa.build_advisory(weather(**hot), crop="Wheat", growth_stage="mid")
    assert insight(general, "heat")["level"] == "moderate"
    h = insight(wheat, "heat")
    assert h["level"] == "moderate" and "Wheat" in h["message"] and "Wheat" in h["basis"]


@pytest.mark.parametrize("tmax,level", [(34.9, "low"), (35.0, "moderate"), (37.9, "moderate"), (38.0, "high")])
def test_wheat_crop_threshold_boundaries(tmax, level):
    adv = fa.build_advisory(weather(temp_max=[tmax] + [30.0] * 6), crop="wheat", growth_stage="mid")
    assert insight(adv, "heat")["level"] == level


def test_crop_threshold_not_applied_outside_sensitive_stage_or_without_stage():
    w = weather(temp_max=[36.0] + [30.0] * 6)
    for stage in (None, "initial", "late"):
        h = insight(fa.build_advisory(w, crop="wheat", growth_stage=stage), "heat")
        assert "Indicative heat-stress threshold" not in h["basis"]


def test_crop_without_specific_threshold_falls_back_to_general_rule():
    w = weather(temp_max=[36.0] + [30.0] * 6)
    h = insight(fa.build_advisory(w, crop="onion", growth_stage="mid"), "heat")
    assert "General heuristic" in h["basis"] and h["level"] == "moderate"


def test_unknown_crop_gets_general_advice_and_an_explicit_limitation():
    adv = fa.build_advisory(weather(), crop="Dragonfruit", growth_stage="mid")
    assert adv["crop"] is None and adv["etc"] is None
    assert any("no crop-specific rules" in l for l in adv["limitations"])


def test_no_crop_selected_states_the_limitation():
    adv = fa.build_advisory(weather())
    assert any("No crop selected" in l for l in adv["limitations"])


@pytest.mark.parametrize("alias,key", [("Paddy (Rice)", "paddy"), ("rice", "paddy"), ("Chana (Gram)", "chickpea"),
                                       (" WHEAT ", "wheat"), ("corn", "maize"), (None, None), ("", None), ("xyz", None)])
def test_crop_aliases(alias, key):
    assert fa.resolve_crop(alias) == key


# ---- wind ----------------------------------------------------------------

@pytest.mark.parametrize("gust,level", [(39.9, "low"), (40.0, "moderate"), (59.9, "moderate"), (60.0, "high")])
def test_wind_boundaries_use_gusts_when_available(gust, level):
    adv = fa.build_advisory(weather(wind_gusts_kmh=[gust] + [10.0] * 6, wind_speed_kmh=5.0))
    assert insight(adv, "wind")["level"] == level


def test_wind_falls_back_to_sustained_speed_when_gusts_missing():
    adv = fa.build_advisory(weather(wind_gusts_kmh=None, wind_speed_kmh=[45.0] + [5.0] * 6))
    assert insight(adv, "wind")["level"] == "moderate" and "winds" in insight(adv, "wind")["message"]


# ---- rain / waterlogging -----------------------------------------------------

@pytest.mark.parametrize("rain,level", [(64.4, "low"), (64.5, "high")])
def test_single_day_heavy_rain_boundary(rain, level):
    # 64.4 mm on one day: below the IMD heavy class and the 3-day total is also
    # < 64.5, so low. 64.5 mm reaches the heavy class -> high.
    adv = fa.build_advisory(weather(rainfall_mm=[rain, 0, 0, 0, 0, 0, 0]))
    assert insight(adv, "heavy_rain")["level"] == level


def test_heavy_rain_high_when_any_day_reaches_imd_heavy():
    adv = fa.build_advisory(weather(rainfall_mm=[0, 64.5, 0, 0, 0, 0, 0]))
    r = insight(adv, "heavy_rain")
    assert r["level"] == "high" and "heavy" in r["trigger"] and "64" in r["trigger"]


def test_three_day_accumulation_gives_moderate_not_high():
    adv = fa.build_advisory(weather(rainfall_mm=[30.0, 20.0, 15.0, 0, 0, 0, 0]))   # 65 mm / 3 d, none >= 64.5
    assert insight(adv, "heavy_rain")["level"] == "moderate"


def test_two_day_total_below_threshold_is_low():
    adv = fa.build_advisory(weather(rainfall_mm=[30.0, 20.0, 14.0, 0, 0, 0, 0]))   # 64 mm / 3 d
    assert insight(adv, "heavy_rain")["level"] == "low"


def test_rain_outlook_recommends_review_not_cancellation():
    adv = fa.build_advisory(weather(rainfall_mm=[0, 20.0, 0, 0, 0, 0, 0]))
    msg = insight(adv, "rain_outlook")["message"].lower()
    assert "review" in msg and "cancel" in msg and "not a reason to cancel" in msg
    assert insight(adv, "rain_outlook")["level"] == "info"


def test_dry_week_outlook_says_plan_irrigation():
    adv = fa.build_advisory(weather(rainfall_mm=0.0))
    assert "Very little rain" in insight(adv, "rain_outlook")["message"]


# ---- ET0 / ETc ---------------------------------------------------------------

@pytest.mark.parametrize("et,band", [(2.9, "low"), (3.0, "moderate"), (5.0, "moderate"), (5.1, "high")])
def test_et0_bands(et, band):
    adv = fa.build_advisory(weather(et0_mm=et))
    assert adv["et0"]["band"] == band and insight(adv, "et0")["level"] == "info"


def test_et0_is_described_as_reference_demand_not_crop_use():
    msg = insight(fa.build_advisory(weather()), "et0")["message"]
    assert "not your crop's actual water use" in msg and "soil moisture" in msg


def test_etc_is_kc_times_et0_with_labelled_assumptions():
    adv = fa.build_advisory(weather(et0_mm=4.0), crop="Wheat", growth_stage="mid")
    etc = adv["etc"]
    assert etc["kc"] == 1.15 and etc["days"] == 7 and etc["etc_mm"] == round(4.0 * 7 * 1.15, 1)
    assert "estimate" in etc["label"].lower() and len(etc["assumptions"]) == 3
    assert any("FAO-56" in a for a in etc["assumptions"])


def test_etc_requires_both_a_known_crop_and_a_stage():
    assert fa.build_advisory(weather(), crop="wheat")["etc"] is None
    assert fa.build_advisory(weather(), growth_stage="mid")["etc"] is None
    assert fa.build_advisory(weather(), crop="wheat", growth_stage="bogus")["etc"] is None


def test_development_stage_kc_is_midpoint_and_disclosed():
    assert fa.kc_for("wheat", "development") == 0.73
    adv = fa.build_advisory(weather(), crop="wheat", growth_stage="development")
    assert any("midpoint" in a for a in adv["etc"]["assumptions"])


def test_etc_omitted_without_et0_data():
    adv = fa.build_advisory(weather(et0_mm=None), crop="wheat", growth_stage="mid")
    assert adv["etc"] is None and adv["et0"] is None
    assert any("Evapotranspiration data is unavailable" in l for l in adv["limitations"])


# ---- spraying windows ----------------------------------------------------------

def test_spraying_window_found_in_calm_dry_daytime_hours():
    adv = fa.build_advisory(weather())     # fixture: wind 8, rain 0%, daytime hours calm
    s = adv["activities"]["spraying"]
    assert s["windows"] and s["windows"][0]["hours"] >= 2
    assert "product label" in s["message"].lower()
    for w in s["windows"]:
        assert w["max_wind_kmh"] <= fa.SPRAY_MAX_WIND_KMH


def test_no_window_when_windy():
    def edit(h):
        for r in h: r["wind_speed_kmh"] = 18.0
    s = fa.build_advisory(weather(hourly_edit=edit))["activities"]["spraying"]
    assert s["windows"] == [] and "No suitable spraying window" in s["message"]


@pytest.mark.parametrize("wind,ok", [(15.0, True), (15.1, False)])
def test_spray_wind_boundary(wind, ok):
    def edit(h):
        for r in h: r["wind_speed_kmh"] = wind
    assert bool(fa.build_advisory(weather(hourly_edit=edit))["activities"]["spraying"]["windows"]) is ok


@pytest.mark.parametrize("prob,ok", [(20.0, True), (20.1, False)])
def test_spray_rain_probability_boundary(prob, ok):
    def edit(h):
        for r in h: r["rain_probability"] = prob
    assert bool(fa.build_advisory(weather(hourly_edit=edit))["activities"]["spraying"]["windows"]) is ok


def test_rain_in_the_following_hours_blocks_the_hour_before_it():
    def edit(h):
        for r in h:
            if r["time"] == "2026-10-19T16:00":
                r["rainfall_mm"] = 1.0; r["rain_probability"] = 80
    wins = fa.build_advisory(weather(hourly_edit=edit))["activities"]["spraying"]["windows"]
    today = [w for w in wins if w["start"].startswith("2026-10-19")]
    for w in today:
        assert w["end"] <= "2026-10-19T14:00"   # nothing within 2 h before the rain


def test_missing_hourly_values_never_count_as_suitable():
    def edit(h):
        for r in h: r["wind_speed_kmh"] = None
    assert fa.build_advisory(weather(hourly_edit=edit))["activities"]["spraying"]["windows"] == []


def test_night_hours_are_excluded():
    wins = fa.build_advisory(weather())["activities"]["spraying"]["windows"]
    assert wins
    for w in wins:
        assert w["start"][11:16] >= "06:00"      # sunrise 06:05 -> first daylight hour starts 07:00
        assert w["end"][11:16] <= "18:00"        # sunset 17:40 -> last hour starts 17:00


def test_past_hours_are_never_part_of_a_spraying_window():
    wins = fa.build_advisory(weather())["activities"]["spraying"]["windows"]
    assert all(w["start"] >= "2026-10-19T14:00" for w in wins)


def test_no_hourly_data_means_spraying_not_assessed():
    adv = fa.build_advisory(weather(hourly_edit=lambda h: h.clear()))
    assert "spraying" not in adv["activities"]
    assert any("spraying windows cannot be assessed" in l for l in adv["limitations"])


# ---- harvest / sowing windows ----------------------------------------------------

def test_harvest_window_needs_consecutive_dry_days():
    w = weather(rainfall_mm=[0, 0, 0, 30, 0, 30, 0], rainfall_probability=[10, 10, 10, 90, 10, 90, 10])
    win = fa.build_advisory(w)["activities"]["harvesting"]["window"]
    assert win["days"] == 3 and win["start"] == "2026-10-19" and win["end"] == "2026-10-21"


def test_no_harvest_window_when_every_dry_day_is_isolated():
    w = weather(rainfall_mm=[0, 30, 0, 30, 0, 30, 0], rainfall_probability=[10, 90, 10, 90, 10, 90, 10])
    h = fa.build_advisory(w)["activities"]["harvesting"]
    assert "window" not in h and "No dry spell" in h["message"]


@pytest.mark.parametrize("mm,prob,dry", [(2.49, 40, True), (2.5, 40, False), (1.0, 41, False), (0, 40, True)])
def test_dry_day_boundary(mm, prob, dry):
    runs = fa.dry_day_runs([{"date": "2026-10-19", "rainfall_mm": mm, "rainfall_probability": prob, "wind_speed_kmh": 5, "wind_gusts_kmh": 10}])
    assert bool(runs) is dry


def test_sowing_text_states_it_cannot_judge_soil_or_calendar():
    s = fa.build_advisory(weather())["activities"]["sowing"]
    assert "soil moisture" in s["message"] and "crop calendar" in s["message"]


# ---- honesty / data quality --------------------------------------------------------

def test_unavailable_or_empty_weather_returns_not_available():
    for w in (None, {}, {"status": "UNAVAILABLE", "forecast": []}, {"status": "LIVE", "forecast": []}):
        adv = fa.build_advisory(w)
        assert adv["available"] is False and adv["insights"] == [] and adv["summary"] is None


def test_demo_and_stale_data_are_disclosed_first():
    demo = fa.build_advisory(weather(status="DEMO"))
    assert demo["limitations"][0].startswith("This advice is based on demonstration data")
    w = weather(status="STALE"); w["cache"] = {"age_seconds": 7200}
    stale = fa.build_advisory(w)
    assert "saved forecast" in stale["limitations"][0] and "120 minutes" in stale["limitations"][0]


def test_every_insight_explains_its_trigger_and_basis():
    adv = fa.build_advisory(weather(), crop="wheat", growth_stage="mid")
    all_items = adv["insights"] + list(adv["activities"].values())
    assert all_items
    for i in all_items:
        assert i["trigger"] and i["basis"] and i["message"] and i["level"] in ("low", "moderate", "high", "info")


def test_limitations_always_deny_guarantees():
    lim = " ".join(fa.build_advisory(weather())["limitations"]).lower()
    assert "cannot predict crop health, disease or yield" in lim


def test_summary_leads_with_highest_risk():
    adv = fa.build_advisory(weather(rainfall_mm=[0, 80.0, 0, 0, 0, 0, 0], temp_max=[41.0] + [30.0] * 6))
    assert adv["summary"].startswith("Heat stress") or adv["summary"].startswith("Heavy rain")
    assert "Heat stress" in adv["summary"] or "Heavy rain" in adv["summary"]


def test_calm_week_summary_is_calm():
    adv = fa.build_advisory(weather(rainfall_mm=0.0, temp_max=30.0, temp_min=20.0, wind_gusts_kmh=15.0, wind_speed_kmh=8.0))
    assert adv["summary"].startswith("No weather risks stand out")


def test_sparse_forecast_rows_do_not_crash():
    w = weather(days=2)
    for d in w["forecast"]:
        for k in ("temp_min", "wind_speed_kmh", "wind_gusts_kmh", "et0_mm", "rainfall_probability"):
            d[k] = None
    adv = fa.build_advisory(w, crop="wheat", growth_stage="mid")
    assert adv["available"] is True


def test_supported_crops_and_stages_are_exposed_for_the_ui():
    adv = fa.build_advisory(weather())
    assert {"key": "wheat", "label": "Wheat"} in adv["supported_crops"]
    assert [s["key"] for s in adv["growth_stages"]] == ["initial", "development", "mid", "late"]
