import datetime as dt
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app import models
from app.config import Settings
from app.mock_data.crops import CROPS, CROP_BY_NAME
from app.mock_data.locations import MARKETS, distance_between
from app.services.transport_optimizer import net_profit_breakdown
from app.services import live_market_data, mandi_directory

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/crops")
def get_crops():
    return CROPS


@router.get("/markets")
def get_markets():
    return MARKETS


@router.get("/live-markets")
def live_markets(state: str = "Chhattisgarh"):
    """
    Official mandi/market names the live government dataset actually has
    for this state right now (discovery, not CropWise's internal town
    list) -- see app/services/mandi_directory.py. Empty list simply means
    live data isn't configured or the discovery call didn't return
    anything (never raises).
    """
    names = mandi_directory.discover_state_markets(state)
    return {
        "state": state,
        "live_data_configured": live_market_data.is_configured(),
        "official_market_names": names,
        "note": (
            "Discovered directly from data.gov.in (Agmarknet), not CropWise's "
            "internal town list. Empty when live data isn't configured, or "
            "the discovery request didn't succeed."
        ),
    }


@router.get("/data-source-status")
def data_source_status():
    """
    Lets the frontend show an accurate 🟢 Live / 🟡 Demo badge without
    guessing -- reflects the actual configured/available data source.

    BUGFIX: this now re-reads configuration fresh on every call via a new
    Settings() instance, instead of relying on the module-level `settings`
    singleton captured once at process startup. Root cause of the reported
    inconsistency (settings.market_data_source / is_configured() showed
    "live"/True when checked directly, but this endpoint still reported
    false): the singleton is only built once, at import time; editing
    .env after the server process has already started does not update it,
    and `uvicorn --reload` does not restart on .env changes (it only
    watches *.py files). A fresh diagnostic script/shell always re-reads
    .env correctly because it's a brand-new process -- the long-running
    server did not. Reproduced exactly: started a server before .env
    contained live config, then edited .env in place without restarting;
    the old code kept returning false indefinitely, this fix picks up the
    change on the very next request with no restart needed.

    This does not change is_configured()'s default behavior for any other
    caller (fetch_live_price_status, /market/live-markets, etc. all still
    use the shared startup-time singleton, unchanged), does not touch how
    the API key is used/sent, and does not alter the live-fetch
    architecture at all -- it only makes this one status-reporting
    endpoint immune to "forgot to restart after editing .env".
    """
    current = Settings()
    configured = live_market_data.is_configured(current)
    return {
        "live_data_configured": configured,
        "provider": "data.gov.in (Agmarknet)" if configured else None,
        "fallback": "Demo/seeded mandi-style dataset",
        "note": (
            "When live data is configured, CropWise attempts a live fetch per "
            "market/crop (trying the official mandi name(s) discovered for "
            "that town, not just its local name) and transparently falls "
            "back to the demo dataset (labeled per-record) if the live "
            "source has no data for that combination or is unreachable."
        ),
    }


def _latest_price_row(db: Session, crop: str, market: str):
    return (
        db.query(models.MarketPrice)
        .filter(models.MarketPrice.crop == crop, models.MarketPrice.market == market)
        .order_by(models.MarketPrice.date.desc())
        .first()
    )


def _record_live_snapshot(db: Session, crop: str, local_market: str, live: dict) -> None:
    """
    Persist a genuine live fetch result as a real MarketPrice row
    (data_source="live") so honest historical trend data actually
    accumulates over time. Upserts on (crop, market, date) so re-fetching
    the same day's data (e.g. from the 10-minute cache expiring and being
    re-hit) doesn't create duplicate rows. Never raises -- a persistence
    hiccup should never break the price-lookup request that triggered it.
    """
    date_str = live.get("arrival_date") or dt.date.today().isoformat()
    try:
        existing = (
            db.query(models.MarketPrice)
            .filter(
                models.MarketPrice.crop == crop,
                models.MarketPrice.market == local_market,
                models.MarketPrice.date == date_str,
                models.MarketPrice.data_source == "live",
            )
            .first()
        )
        if existing:
            existing.min_price = live["min_price"]
            existing.max_price = live["max_price"]
            existing.modal_price = live["modal_price"]
        else:
            db.add(models.MarketPrice(
                crop=crop, market=local_market, date=date_str,
                min_price=live["min_price"], max_price=live["max_price"],
                modal_price=live["modal_price"],
                # This data.gov.in resource does not provide arrival
                # volume -- store None ("not available"), never 0.0.
                # A fabricated 0 would be indistinguishable from a
                # genuine zero-arrivals day and would silently corrupt
                # arrival_intelligence()'s trend/demand-signal math once
                # live rows are mixed with demo history (see that
                # endpoint for how None is now excluded from averages).
                arrivals_tonnes=None,
                data_source="live",
            ))
        db.commit()
    except Exception:
        db.rollback()


def _get_price(db: Session, crop: str, market: str) -> dict:
    """
    Real price lookup with four distinct, honestly-reported outcomes (see
    mandi_directory.fetch_price_result for the full status contract):

      status="ok"             -> live government price, data_source="live".
                                  source_resource="market" is a genuine
                                  mandi-specific record ("Government Mandi
                                  Price"); source_resource="district_variety"
                                  is the aggregated fallback resource
                                  ("District Reference Price") and is NEVER
                                  presented as a mandi modal price -- see
                                  `district_reference_note`.
      status="no_records"     -> both live resources responded but neither
                                  has a record for this exact crop/market/
                                  state selection. Per spec this must NOT
                                  fall back to demo data -- returned as-is
                                  so the caller shows "No official
                                  government record found for this
                                  selection."
      status="error"          -> at least one live resource itself failed
                                  (network/auth/format). THIS falls back to
                                  the demo dataset, tagged data_source="demo".
      status="not_configured" -> live data isn't set up at all -- the
                                  normal state for a demo deployment, not a
                                  failure. Also falls back to demo data, but
                                  without an "unavailable" framing.

    Only a genuine mandi-level ("market") hit is persisted into the
    historical MarketPrice series (see `_record_live_snapshot`) -- a
    district-level aggregate is a different granularity and must never be
    silently blended into the same per-market history.

    Always returns a dict (never None) so callers check `status`/
    `data_source` instead of special-casing a missing return value.
    """
    outcome = mandi_directory.fetch_price_result(crop, market)

    if outcome["status"] == "ok":
        live = outcome["data"]
        is_market_level = live.get("source_resource") == "market"
        if is_market_level:
            _record_live_snapshot(db, crop, market, live)
        return {
            "status": "ok", "data_source": "live",
            "modal_price": live["modal_price"], "min_price": live["min_price"],
            "max_price": live["max_price"], "date": live.get("arrival_date") or "",
            "arrivals_tonnes": None,
            "matched_market_name": live.get("matched_market_name", market),
            "district": mandi_directory.LOCAL_MARKET_TO_DISTRICT.get(market, market),
            "variety": live.get("variety") if is_market_level else None,
            "grade": live.get("grade") if is_market_level else None,
            "varieties": live.get("varieties") if not is_market_level else None,
            "fetched_at": live.get("fetched_at"),
            "source_resource": live.get("source_resource"),
            "district_reference_note": live.get("district_reference_note"),
            "message": None,
        }

    if outcome["status"] == "no_records":
        return {
            "status": "no_records", "data_source": None,
            "message": "No official government record found for this selection.",
        }

    # status in {"error", "not_configured"} -- both fall back to the demo
    # dataset; only the message framing differs, since an "unavailable"
    # note is only fair when live data was actually configured and
    # something genuinely went wrong, not when it was simply never set up.
    demo_row = _latest_price_row(db, crop, market)
    if not demo_row:
        return {
            "status": outcome["status"], "data_source": None,
            "message": (
                "🟡 Demo Data — Government API unavailable, and no demo data seeded for this market."
                if outcome["status"] == "error" else
                "No demo data seeded for this market."
            ),
        }
    return {
        "status": outcome["status"], "data_source": "demo",
        "modal_price": demo_row.modal_price, "min_price": demo_row.min_price,
        "max_price": demo_row.max_price, "date": demo_row.date,
        "arrivals_tonnes": demo_row.arrivals_tonnes,
        "matched_market_name": market,
        "district": mandi_directory.LOCAL_MARKET_TO_DISTRICT.get(market, market),
        "variety": None, "grade": None, "varieties": None,
        "fetched_at": None, "source_resource": None, "district_reference_note": None,
        "message": (
            "🟡 Demo Data — Government API unavailable." if outcome["status"] == "error"
            else "🟡 Demo Data"
        ),
    }


def _history_rows(db: Session, crop: str, market: str, days: Optional[int] = None,
                   data_source: Optional[str] = None):
    q = (
        db.query(models.MarketPrice)
        .filter(models.MarketPrice.crop == crop, models.MarketPrice.market == market)
    )
    if data_source:
        q = q.filter(models.MarketPrice.data_source == data_source)
    rows = q.order_by(models.MarketPrice.date.asc()).all()
    if days:
        rows = rows[-days:]
    return rows


UNAVAILABLE_MESSAGE = "Historical mandi data is currently unavailable."


@router.get("/prices")
def get_prices(crop: str, market: str, days: int = 30, include_demo: bool = False,
                db: Session = Depends(get_db)):
    """
    Historical price series for a crop/market.

    HONESTY: by default this returns ONLY genuine data points -- rows with
    data_source="live", i.e. real snapshots CropWise itself captured from
    data.gov.in over time (see `_record_live_snapshot`). It does NOT
    return the synthesized 60-day demo series here, because that series is
    not real historical data and must never be presented as a real price
    trend. If there isn't enough genuine history yet, `available` is
    false and `message` explains why -- the frontend should show that
    message instead of drawing a chart.

    Pass `include_demo=true` to explicitly opt into the clearly-labeled
    synthetic demo series instead (e.g. for a hackathon walkthrough) --
    every row it returns is still tagged `data_source: "demo"` so it can
    never be mistaken for real data downstream.
    """
    if crop not in CROP_BY_NAME:
        raise HTTPException(status_code=404, detail="Unknown crop")

    rows = _history_rows(db, crop, market, days, data_source="live")
    if rows:
        return {
            "crop": crop, "market": market, "available": True,
            "data_source": "live", "is_demo": False, "message": None,
            "rows": [
                {"date": r.date, "min_price": r.min_price, "max_price": r.max_price,
                 "modal_price": r.modal_price, "arrivals_tonnes": r.arrivals_tonnes,
                 "data_source": r.data_source}
                for r in rows
            ],
        }

    if include_demo:
        demo_rows = _history_rows(db, crop, market, days, data_source="demo")
        return {
            "crop": crop, "market": market, "available": bool(demo_rows),
            "data_source": "demo" if demo_rows else None, "is_demo": True,
            "message": (None if demo_rows else UNAVAILABLE_MESSAGE),
            "demo_disclaimer": (
                "Simulated for demonstration only -- not real government "
                "mandi data. Requested explicitly via include_demo=true."
            ) if demo_rows else None,
            "rows": [
                {"date": r.date, "min_price": r.min_price, "max_price": r.max_price,
                 "modal_price": r.modal_price, "arrivals_tonnes": r.arrivals_tonnes,
                 "data_source": r.data_source}
                for r in demo_rows
            ],
        }

    return {
        "crop": crop, "market": market, "available": False,
        "data_source": None, "is_demo": False, "message": UNAVAILABLE_MESSAGE,
        "rows": [],
    }


@router.get("/compare")
def compare_markets(
    crop: str = Query(...), quantity_kg: float = Query(...), location: str = Query(...),
    top_n: int = 6, db: Session = Depends(get_db),
):
    if crop not in CROP_BY_NAME:
        raise HTTPException(status_code=404, detail="Unknown crop")
    if quantity_kg <= 0:
        raise HTTPException(status_code=400, detail="quantity_kg must be positive")

    candidate_markets = sorted(MARKETS, key=lambda m: distance_between(location, m["name"]))[:top_n]

    options = []
    # Markets where the government API responded successfully but had no
    # record for this exact selection. Per spec these are honestly
    # reported, never silently backfilled with demo numbers.
    unavailable_markets = []
    any_live = False
    for m in candidate_markets:
        latest = _get_price(db, crop, m["name"])

        if latest["status"] == "no_records":
            unavailable_markets.append({"market": m["name"], "message": latest["message"]})
            continue
        if latest.get("data_source") is None:
            # error/not_configured AND no demo data seeded for this market
            # either -- genuinely nothing to show, not the same as
            # no_records (the live API wasn't reachable at all here).
            continue

        if latest["data_source"] == "live":
            any_live = True
        price_per_kg = round(latest["modal_price"] / 100.0, 2)
        distance = distance_between(location, m["name"])
        breakdown = net_profit_breakdown(quantity_kg, price_per_kg, distance)
        options.append({
            "market": m["name"],
            "distance_km": distance,
            "modal_price_per_kg": price_per_kg,
            "min_price_per_kg": round(latest["min_price"] / 100.0, 2),
            "max_price_per_kg": round(latest["max_price"] / 100.0, 2),
            "arrivals_tonnes": latest["arrivals_tonnes"],
            "as_of_date": latest["date"],
            "data_source": latest["data_source"],  # "live" | "demo" -- per-market, never blended silently
            "source_resource": latest.get("source_resource"),  # "market" | "district_variety" | None
            "matched_market_name": latest.get("matched_market_name", m["name"]),
            "district_reference_note": latest.get("district_reference_note"),
            **breakdown,
            "net_profit_is_estimated": True,
        })

    if not options:
        return {
            "crop": crop, "quantity_kg": quantity_kg, "location": location,
            "options": [], "recommended_market": None,
            "insufficient_data": True,
            "message": "Insufficient data to make a reliable recommendation.",
            "why": None,
            "profit_gain_vs_nearest_market": 0,
            "data_source_summary": None,
            "unavailable_markets": unavailable_markets,
        }

    options.sort(key=lambda o: o["net_profit"], reverse=True)
    best = options[0]
    nearest_option = min(options, key=lambda o: o["distance_km"])
    profit_gain_vs_nearest = round(best["net_profit"] - nearest_option["net_profit"], 2)

    why = _explain_recommendation(best, nearest_option, options)

    return {
        "crop": crop,
        "quantity_kg": quantity_kg,
        "location": location,
        "options": options,
        "recommended_market": best["market"],
        "insufficient_data": False,
        "message": None,
        "why": why,
        "profit_gain_vs_nearest_market": max(profit_gain_vs_nearest, 0),
        "data_source_summary": "live" if any_live else "demo",
        "unavailable_markets": unavailable_markets,
    }


def _explain_recommendation(best: dict, nearest: dict, options: list) -> str:
    """
    Plain-language explanation of why `best` was recommended. Built only
    from figures already computed for this request -- no invented
    numbers -- and always frames the net-profit figures as estimates.
    """
    if best["market"] == nearest["market"]:
        return (
            f"{best['market']} is both the nearest option and gives the highest estimated "
            f"net return among the markets compared, after estimated transport, commission, "
            f"and handling costs."
        )

    highest_price_option = max(options, key=lambda o: o["modal_price_per_kg"])
    if highest_price_option["market"] != best["market"] and highest_price_option["modal_price_per_kg"] > best["modal_price_per_kg"]:
        return (
            f"Although {highest_price_option['market']} has a higher mandi price "
            f"(₹{highest_price_option['modal_price_per_kg']}/kg vs ₹{best['modal_price_per_kg']}/kg), "
            f"the estimated transportation and mandi costs to reach it reduce that advantage. "
            f"Based on the available inputs, {best['market']} currently gives the highest "
            f"estimated net return (≈₹{best['net_profit']:,} on this quantity)."
        )

    return (
        f"{best['market']} gives the highest estimated net return (≈₹{best['net_profit']:,} on this "
        f"quantity) among the markets compared, after estimated transport, commission, and "
        f"handling costs -- {best['distance_km']} km away vs {nearest['distance_km']} km for the "
        f"nearest option."
    )


# ─── Phase 8: Arrival Volume Intelligence ────────────────────────────────────

@router.get("/arrivals")
def arrival_intelligence(
    crop: str = Query(...),
    market: str = Query(...),
    days: int = Query(14, ge=3, le=60),
    db: Session = Depends(get_db),
):
    """
    Return arrival volumes + price trend for a crop/market combination.
    Uses existing MarketPrice.arrivals_tonnes from the seeded dataset.
    Data source is clearly labelled per-row.
    """
    if crop not in CROP_BY_NAME:
        raise HTTPException(status_code=404, detail="Unknown crop")

    rows = _history_rows(db, crop, market, days)
    if not rows:
        return {
            "crop": crop, "market": market, "available": False,
            "is_demo": False,
            "demo_disclaimer": None,
            "message": "No arrival data found for this crop/market.",
            "data": [],
            "summary": None,
        }

    data = [
        {
            "date": r.date,
            "arrivals_tonnes": r.arrivals_tonnes,
            "modal_price": round(r.modal_price / 100.0, 2),
            "min_price": round(r.min_price / 100.0, 2),
            "max_price": round(r.max_price / 100.0, 2),
            "data_source": r.data_source,
        }
        for r in rows
    ]

    # compute summary signals
    latest = data[-1]
    prev = data[-2] if len(data) >= 2 else None
    week_slice = data[-7:] if len(data) >= 7 else data
    two_week_slice = data[-14:] if len(data) >= 14 else data

    arrival_change_pct = None
    price_change_pct = None
    if prev:
        # Guard against None (live rows genuinely have no arrival-volume
        # field from this data.gov.in resource -- treat as "unavailable",
        # never as a real zero, so a live day doesn't fake a -100% arrival
        # swing or drag the averages below down to a false "oversupply"
        # signal).
        if prev["arrivals_tonnes"] is not None and latest["arrivals_tonnes"] is not None and prev["arrivals_tonnes"] > 0:
            arrival_change_pct = round(
                (latest["arrivals_tonnes"] - prev["arrivals_tonnes"]) / prev["arrivals_tonnes"] * 100, 1
            )
        if prev["modal_price"] and prev["modal_price"] > 0:
            price_change_pct = round(
                (latest["modal_price"] - prev["modal_price"]) / prev["modal_price"] * 100, 1
            )

    _week_known = [d["arrivals_tonnes"] for d in week_slice if d["arrivals_tonnes"] is not None]
    _2w_known = [d["arrivals_tonnes"] for d in two_week_slice if d["arrivals_tonnes"] is not None]
    avg_arrivals_week = round(sum(_week_known) / len(_week_known), 1) if _week_known else None
    avg_arrivals_2w = round(sum(_2w_known) / len(_2w_known), 1) if _2w_known else None

    # demand signal
    if arrival_change_pct is not None and price_change_pct is not None:
        if arrival_change_pct < -10 and price_change_pct > 0:
            demand_signal = "STRONG"
            signal_explanation = "Arrivals falling while price rising — strong demand signal"
        elif arrival_change_pct > 10 and price_change_pct < 0:
            demand_signal = "WEAK"
            signal_explanation = "Arrivals increasing while price falling — oversupply signal"
        elif price_change_pct > 3:
            demand_signal = "POSITIVE"
            signal_explanation = "Price trending upward"
        elif price_change_pct < -3:
            demand_signal = "NEGATIVE"
            signal_explanation = "Price trending downward"
        else:
            demand_signal = "NEUTRAL"
            signal_explanation = "Price and arrivals stable"
    else:
        demand_signal = "UNKNOWN"
        signal_explanation = "Insufficient comparison data"

    is_demo = all(d["data_source"] == "demo" for d in data)

    return {
        "crop": crop,
        "market": market,
        "available": True,
        "is_demo": is_demo,
        "demo_disclaimer": (
            "⚠️ Demo data — not a real-time government mandi feed. "
            "Add a data.gov.in API key to enable live arrival data."
        ) if is_demo else None,
        "summary": {
            "latest_date": latest["date"],
            "today_arrivals_tonnes": latest["arrivals_tonnes"],
            "yesterday_arrivals_tonnes": prev["arrivals_tonnes"] if prev else None,
            "arrival_change_pct": arrival_change_pct,
            "modal_price": latest["modal_price"],
            "min_price": latest["min_price"],
            "max_price": latest["max_price"],
            "price_change_pct": price_change_pct,
            "avg_arrivals_7d": avg_arrivals_week,
            "avg_arrivals_14d": avg_arrivals_2w,
            "demand_signal": demand_signal,
            "signal_explanation": signal_explanation,
        },
        "data": data,
    }


@router.get("/selling-window")
def selling_window(
    crop: str = Query(...),
    market: str = Query(...),
    quantity_kg: float = Query(..., gt=0),
    storage_cost_per_kg_per_day: float = Query(0.05),
    db: Session = Depends(get_db),
):
    """
    Phase 7 — Best Selling Window recommendation.
    Combines price forecast + storage cost to find optimal sell timing.
    Based entirely on available forecast data — never invents predictions.
    """
    if crop not in CROP_BY_NAME:
        raise HTTPException(status_code=404, detail="Unknown crop")

    # Get current price
    current = _get_price(db, crop, market)
    if current.get("data_source") is None:
        raise HTTPException(status_code=404, detail="No price data available for this market")

    current_price = round(current["modal_price"] / 100.0, 2)

    # Get history for forecast
    rows = _history_rows(db, crop, market)
    is_demo = all(r.data_source == "demo" for r in rows) if rows else True
    history = [{"date": r.date, "modal_price": round(r.modal_price / 100.0, 2),
                "arrivals_tonnes": r.arrivals_tonnes} for r in rows]

    if not history:
        raise HTTPException(status_code=404, detail="Insufficient history for forecast")

    from app.services.price_predictor import predict_next_days
    forecast_dict = predict_next_days(history, days=15)
    # Convert daily_predictions list into list-of-dicts for slicing
    daily_preds = forecast_dict.get("daily_predictions", [])
    forecast_list = [{"predicted_price": p} for p in daily_preds]

    # Build options: SELL_NOW, WAIT_5, WAIT_7, STORE_15
    options = []

    def _window_option(label: str, days: int, forecast_slice: list) -> dict:
        if not forecast_slice:
            return None
        prices = [f["predicted_price"] for f in forecast_slice if f.get("predicted_price")]
        if not prices:
            return None
        avg_price = round(sum(prices) / len(prices), 2)
        max_price = round(max(prices), 2)
        storage_cost = round(quantity_kg * storage_cost_per_kg_per_day * days, 2)
        gross_revenue = round(avg_price * quantity_kg, 2)
        net_revenue = round(gross_revenue - storage_cost, 2)
        current_revenue = round(current_price * quantity_kg, 2)
        additional_revenue = round(net_revenue - current_revenue, 2)
        # risk: higher variance = higher risk
        if len(prices) > 1:
            variance = sum((p - avg_price) ** 2 for p in prices) / len(prices)
            std_dev = variance ** 0.5
            cv = std_dev / avg_price if avg_price else 0
            risk = "HIGH" if cv > 0.05 else ("MEDIUM" if cv > 0.02 else "LOW")
        else:
            risk = "MEDIUM"
        return {
            "label": label,
            "days_to_wait": days,
            "expected_price_range": {
                "min": round(min(prices), 2),
                "max": max_price,
                "avg": avg_price,
            },
            "storage_cost": storage_cost,
            "estimated_gross_revenue": gross_revenue,
            "estimated_net_revenue": net_revenue,
            "additional_revenue_vs_now": additional_revenue,
            "risk": risk,
        }

    options.append({
        "label": "SELL_NOW",
        "days_to_wait": 0,
        "expected_price_range": {"min": current_price, "max": current_price, "avg": current_price},
        "storage_cost": 0,
        "estimated_gross_revenue": round(current_price * quantity_kg, 2),
        "estimated_net_revenue": round(current_price * quantity_kg, 2),
        "additional_revenue_vs_now": 0,
        "risk": "LOW",
    })

    for label, days in [("WAIT_5_DAYS", 5), ("WAIT_7_DAYS", 7), ("STORE_15_DAYS", 15)]:
        slice_ = forecast_list[:days]
        opt = _window_option(label, days, slice_)
        if opt:
            options.append(opt)

    # Recommend: best net revenue
    best = max(options, key=lambda o: o["estimated_net_revenue"])

    return {
        "crop": crop,
        "market": market,
        "quantity_kg": quantity_kg,
        "current_price": current_price,
        "is_demo": is_demo,
        "forecast_disclaimer": (
            "⚠️ Demo forecast — based on simulated mandi data, not a real government feed."
        ) if is_demo else "Based on available historical data. Forecasts are estimates only.",
        "recommendation": best["label"],
        "recommendation_explanation": (
            f"Waiting {best['days_to_wait']} day(s) gives estimated net revenue of "
            f"₹{best['estimated_net_revenue']:,.0f} vs ₹{round(current_price * quantity_kg):,} now, "
            f"after ₹{best['storage_cost']:,.0f} estimated storage cost. Risk: {best['risk']}."
            if best["days_to_wait"] > 0 else
            "Selling now gives the best estimated net return given current forecast."
        ),
        "options": options,
    }
