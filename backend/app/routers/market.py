import datetime as dt
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app import models
from app.mock_data.crops import CROPS, CROP_BY_NAME
from app.mock_data.locations import MARKETS, distance_between, nearest_market_to_coordinates, haversine_km
from app.services.transport_optimizer import net_profit_breakdown
from app.services import live_market_data, mandi_directory, agmarknet_service
from app.config import logger, settings

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/crops")
def get_crops():
    return CROPS


@router.get("/markets")
def get_markets():
    return MARKETS


@router.get("/nearest-market")
def nearest_market(latitude: float, longitude: float):
    """Resolve raw GPS coordinates (from the browser's geolocation API) to
    the nearest known CropWise market, pan-India. This is what lets granted
    location permission genuinely override the configurable demo default
    (Settings.default_demo_state) instead of the frontend staying pinned to
    the demo region's town regardless of where the user actually is."""
    match = nearest_market_to_coordinates(latitude, longitude)
    if not match:
        raise HTTPException(status_code=404, detail="No known markets configured")
    return {
        "market": match["name"],
        "state": match["state"],
        "latitude": match["latitude"],
        "longitude": match["longitude"],
        "distance_km": round(haversine_km(latitude, longitude, match["latitude"], match["longitude"]), 1),
    }


@router.get("/live-markets")
def live_markets(state: str = settings.default_demo_state):
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
    """Lets the frontend show an accurate 🟢 Live / 🟡 Demo badge without
    guessing -- reflects the actual configured/available data source."""
    return {
        "live_data_configured": (
            live_market_data.is_configured() or agmarknet_service.is_configured()
        ),
        "provider": (
            agmarknet_service.status()["provider"]
            or ("data.gov.in (Agmarknet)" if live_market_data.is_configured() else None)
        ),
        "providers": {
            "data.gov.in": {
                "configured": live_market_data.is_configured(),
                "available": live_market_data.is_configured(),
            },
            "CEDA_AGMARKNET": agmarknet_service.status(),
        },
        "fallback": "Demo/seeded mandi-style dataset",
        "note": (
            "CropWise tries data.gov.in first, then CEDA AGMARKNET when "
            "configured, and transparently falls back to the seeded dataset "
            "(labeled per-record) when live sources are unavailable."
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
    except Exception as e:
        # Deliberately broad: this wraps a best-effort DB persist of a live
        # snapshot. A persistence hiccup here must never break the price
        # lookup request that triggered it -- but log it (not silent) so a
        # real, recurring failure is still visible in server logs.
        db.rollback()
        logger.debug("_record_live_snapshot failed for %s/%s: %s", crop, local_market, e)


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
    outcome = mandi_directory.fetch_price_result(
        crop, market, state=mandi_directory.state_for_market(market),
    )

    if outcome["status"] == "ok":
        live = outcome["data"]
        is_market_level = live.get("source_resource") == "market"
        if is_market_level:
            _record_live_snapshot(db, crop, market, live)
        return {
            "status": "ok", "data_source": "live",
            "provider": live.get("source", live.get("provider", "data.gov.in (Agmarknet)")),
            "modal_price": live["modal_price"], "min_price": live["min_price"],
            "max_price": live["max_price"], "date": live.get("arrival_date") or "",
            "arrivals_tonnes": live.get("quantity"),
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

    # PRODUCT DECISION (explicitly requested by the project owner, superseding
    # the previous stricter behaviour): live data is still always preferred
    # and always tried first above, but the dashboard must never go blank or
    # show a dead end. Every non-"ok" outcome -- a confirmed "no record for
    # this exact selection", a live request that errored/timed out, or live
    # mode simply not being configured -- now falls through to the same
    # seeded demo dataset below, rather than stopping short. The *reason* for
    # the fallback is still preserved in `status`/`message` for transparency
    # and logging; only the "give up and show nothing" behaviour is removed.
    demo_row = _latest_price_row(db, crop, market)
    if not demo_row:
        # Genuine last resort: this exact crop/market combination has no
        # live record AND nothing seeded for it either. Still not "hide the
        # page" -- callers (compare_markets) treat this market as simply not
        # contributing an option, and try further markets instead.
        return {
            "status": "unavailable", "data_source": None,
            "message": "No live or demo data available for this selection.",
        }

    reason_message = {
        "no_records": "🟡 Demo Data — no official government record for this exact selection.",
        "error": "🟡 Demo Data — government market API could not be reached (timeout or request failure).",
        "not_configured": "🟡 Demo Data",
    }.get(outcome["status"], "🟡 Demo Data")
    logger.info("Using demo data (reason=%s) for %s/%s", outcome["status"], crop, market)
    return {
        "status": "demo_fallback", "data_source": "demo",
        # Preserved purely for audit/debugging -- never shown to users as a
        # separate concept from the "demo" badge itself.
        "fallback_reason": outcome["status"],
        "provider": "DEMO",
        "modal_price": demo_row.modal_price, "min_price": demo_row.min_price,
        "max_price": demo_row.max_price, "date": demo_row.date,
        "arrivals_tonnes": demo_row.arrivals_tonnes,
        "matched_market_name": market,
        "district": mandi_directory.LOCAL_MARKET_TO_DISTRICT.get(market, market),
        "variety": None, "grade": None, "varieties": None,
        "fetched_at": None, "source_resource": None, "district_reference_note": None,
        "message": reason_message,
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
    top_n: int = Query(6, ge=1, le=30), db: Session = Depends(get_db),
):
    # compare_markets is called two ways: as an HTTP endpoint (where
    # FastAPI resolves the Query(...) defaults above into real values
    # before this body runs) AND directly as a plain Python function by
    # advisor.py and admin.py, which omit top_n and rely on its default.
    # A direct call never goes through FastAPI's request-parsing layer, so
    # it would receive the raw Query(...) marker object itself instead of
    # 6 -- which crashed every such call with "slice indices must be
    # integers" the moment top_n gained bounds validation. Coerce defensively
    # so both call styles work.
    if not isinstance(top_n, int):
        top_n = 6
    top_n = max(1, min(top_n, 30))

    if crop not in CROP_BY_NAME:
        raise HTTPException(status_code=404, detail="Unknown crop")
    if quantity_kg <= 0:
        raise HTTPException(status_code=400, detail="quantity_kg must be positive")

    all_markets_by_distance = sorted(MARKETS, key=lambda m: distance_between(location, m["name"]))
    candidate_markets = all_markets_by_distance[:top_n]

    # Markets where NEITHER live NOR demo data exists at all -- the one
    # genuine "nothing to show" case left after the fallback below. Kept
    # for transparency (surfaced as `unavailable_markets`), never silently
    # dropped without explanation.
    unavailable_markets = []

    def _try_market(m):
        """Look up one market and return an `options` row, or None if truly
        nothing (live or demo) exists for it."""
        latest = _get_price(db, crop, m["name"])
        if latest.get("data_source") is None:
            unavailable_markets.append({"market": m["name"], "message": latest["message"]})
            return None
        price_per_kg = round(latest["modal_price"] / 100.0, 2)
        distance = distance_between(location, m["name"])
        breakdown = net_profit_breakdown(quantity_kg, price_per_kg, distance)
        return {
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
            "fallback_reason": latest.get("fallback_reason"),  # None when data_source == "live"
            **breakdown,
            "net_profit_is_estimated": True,
        }

    options = []
    considered_names = set()
    for m in candidate_markets:
        considered_names.add(m["name"])
        row = _try_market(m)
        if row:
            options.append(row)

    # Guarantee at least 3 markets to compare whenever the platform knows
    # about 3+ markets at all -- live data is still preferred per market,
    # this only reaches further down the distance-sorted list (never
    # fabricates a market that isn't in MARKETS) when the initial top_n
    # candidates came up short.
    MIN_OPTIONS = 3
    if len(options) < MIN_OPTIONS:
        for m in all_markets_by_distance:
            if len(options) >= MIN_OPTIONS or m["name"] in considered_names:
                continue
            considered_names.add(m["name"])
            row = _try_market(m)
            if row:
                options.append(row)

    if not options:
        # Genuinely nothing -- not even one demo-backed market -- which in
        # practice only happens for a crop with no seeded data at all.
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

    # Bug: this used to be `"live" if any_live else "demo"`, which calls a
    # result set "live" the moment even ONE of several compared markets
    # had a live price -- silently mislabeling a mostly-demo comparison as
    # fully live. Report the actual mix instead.
    _sources_seen = {o["data_source"] for o in options}
    if _sources_seen == {"live"}:
        data_source_summary = "live"
    elif _sources_seen == {"demo"}:
        data_source_summary = "demo"
    elif _sources_seen:
        data_source_summary = "mixed"
    else:
        data_source_summary = "unavailable"  # unreachable in practice (options is non-empty here)

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
        # "live" | "demo" | "mixed" | "unavailable" -- each option's own
        # data_source is still preserved unchanged above; this is only a
        # rollup summary, never a substitute for the per-option field.
        "data_source_summary": data_source_summary,
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

    # ── Arrival-volume honesty (separate from price honesty above) ──
    # Bug: `is_demo` (price) can be False while every arrivals_tonnes
    # figure actually shown/averaged still came from demo rows (live rows
    # from data.gov.in always have arrivals_tonnes=None, since that
    # verified resource does not provide arrival volume at all). That
    # meant a mixed live-price/demo-history result could reach the
    # frontend with `is_demo: false` and no warning, even though every
    # arrival number on screen was seeded demo data. Compute arrival
    # honesty from which rows actually contributed a non-None arrivals
    # figure, not from the overall price data_source mix.
    _arrival_sources_seen = {d["data_source"] for d in data if d["arrivals_tonnes"] is not None}
    if not _arrival_sources_seen:
        arrivals_status = "unavailable"  # no source (live or demo) has an arrival figure at all
    elif _arrival_sources_seen == {"live"}:
        arrivals_status = "live"
    elif _arrival_sources_seen == {"demo"}:
        arrivals_status = "demo"
    else:
        arrivals_status = "mixed"  # some days live (still None today), some days demo-illustrative

    arrivals_demo_disclaimer = (
        "⚠️ Arrival volume shown is DEMO/ILLUSTRATIVE data, not a live government feed. "
        "The verified live mandi-price source (data.gov.in) does not publish arrival "
        "volume, so no live figure is available for this crop/market yet."
    ) if arrivals_status in ("demo", "mixed") else (
        "Arrival volume is not available for this crop/market from any configured source."
        if arrivals_status == "unavailable" else None
    )

    return {
        "crop": crop,
        "market": market,
        "available": True,
        "is_demo": is_demo,
        "demo_disclaimer": (
            "⚠️ Demo data — not a real-time government mandi feed. "
            "Add a data.gov.in API key to enable live arrival data."
        ) if is_demo else None,
        # Dedicated, always-accurate label for the arrival-volume figures
        # specifically -- read this instead of (or alongside) `is_demo`
        # when deciding whether to show an arrival-data warning banner.
        "arrivals_status": arrivals_status,  # "live" | "demo" | "mixed" | "unavailable"
        "arrivals_demo_disclaimer": arrivals_demo_disclaimer,
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
