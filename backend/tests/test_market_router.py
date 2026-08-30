"""
Unit tests for app/routers/market.py's _get_price(), covering the
fallback/no-fallback rules that are the whole point of this hardening
pass:
  - "no_records" must NEVER be silently replaced with demo data.
  - "error" / "not_configured" DO fall back to demo data when seeded.
  - only a genuine mandi-level ("market") hit gets persisted into the
    historical MarketPrice series -- a district-level aggregate must not
    be silently blended into that same per-market history.

Uses an isolated in-memory SQLite database (not the real cropwise.db) and
monkeypatches mandi_directory.fetch_price_result directly, so no network
calls happen and no other test's data can leak in.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models
from app.database import Base
from app.routers import market as market_router
from app.services import mandi_directory


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _seed_demo_row(db, crop="Tomato", market="Bilaspur"):
    db.add(models.MarketPrice(
        crop=crop, market=market, date="2026-08-20",
        min_price=3200.0, max_price=3600.0, modal_price=3400.0,
        arrivals_tonnes=50.0, data_source="demo",
    ))
    db.commit()


def test_ok_market_level_persists_history_and_labels_live(db, monkeypatch):
    monkeypatch.setattr(mandi_directory, "fetch_price_result", lambda crop, market, **k: {
        "status": "ok",
        "data": {
            "modal_price": 3500.0, "min_price": 3300.0, "max_price": 3700.0,
            "arrival_date": "26/08/2026", "matched_market_name": "Bilaspur",
            "variety": "Local", "grade": "FAQ", "fetched_at": "2026-08-26T00:00:00Z",
            "source_resource": "market",
        },
    })

    result = market_router._get_price(db, "Tomato", "Bilaspur")

    assert result["status"] == "ok"
    assert result["data_source"] == "live"
    assert result["source_resource"] == "market"

    persisted = db.query(models.MarketPrice).filter_by(
        crop="Tomato", market="Bilaspur", data_source="live",
    ).all()
    assert len(persisted) == 1
    assert persisted[0].modal_price == 3500.0


def test_ok_district_variety_does_not_pollute_market_history(db, monkeypatch):
    monkeypatch.setattr(mandi_directory, "fetch_price_result", lambda crop, market, **k: {
        "status": "ok",
        "data": {
            "modal_price": 3400.0, "min_price": 3200.0, "max_price": 3600.0,
            "arrival_date": "26/08/2026", "matched_market_name": "Bilaspur (district)",
            "varieties": [{"variety": "Local", "modal_price": 3400.0}],
            "fetched_at": "2026-08-26T00:00:00Z",
            "source_resource": "district_variety",
            "district_reference_note": (
                "Calculated from available variety-level government records; "
                "this is not a specific mandi modal price."
            ),
        },
    })

    result = market_router._get_price(db, "Tomato", "Bilaspur")

    assert result["status"] == "ok"
    assert result["source_resource"] == "district_variety"
    assert "not a specific mandi modal price" in result["district_reference_note"]

    # The critical assertion: a district-aggregate value must never be
    # silently written into the per-market historical price series.
    persisted = db.query(models.MarketPrice).filter_by(crop="Tomato", market="Bilaspur").all()
    assert len(persisted) == 0


def test_no_records_never_falls_back_to_demo_even_if_demo_data_exists(db, monkeypatch):
    _seed_demo_row(db)  # demo data IS available for this market
    monkeypatch.setattr(mandi_directory, "fetch_price_result", lambda crop, market, **k: {
        "status": "no_records", "data": None,
    })

    result = market_router._get_price(db, "Tomato", "Bilaspur")

    assert result["status"] == "no_records"
    assert result["data_source"] is None  # NOT "demo" -- the critical assertion
    assert "No official government record found" in result["message"]


def test_error_falls_back_to_demo_when_seeded(db, monkeypatch):
    _seed_demo_row(db)
    monkeypatch.setattr(mandi_directory, "fetch_price_result", lambda crop, market, **k: {
        "status": "error", "data": None,
    })

    result = market_router._get_price(db, "Tomato", "Bilaspur")

    assert result["status"] == "error"
    assert result["data_source"] == "demo"
    assert "unavailable" in result["message"].lower()


def test_not_configured_falls_back_to_demo_without_unavailable_framing(db, monkeypatch):
    _seed_demo_row(db)
    monkeypatch.setattr(mandi_directory, "fetch_price_result", lambda crop, market, **k: {
        "status": "not_configured", "data": None,
    })

    result = market_router._get_price(db, "Tomato", "Bilaspur")

    assert result["status"] == "not_configured"
    assert result["data_source"] == "demo"
    assert "unavailable" not in result["message"].lower()


# ---------------------------------------------------------------------------
# Regression test for a reported bug: GET /market/data-source-status could
# report live_data_configured=false even though settings.market_data_source,
# settings.data_gov_in_api_key, and live_market_data.is_configured() all
# independently agreed the app WAS configured for live data.
#
# Root cause: app.config.settings is a singleton built once at process
# import time. data_source_status() used to read that singleton directly,
# so a long-running server process whose .env was created/edited AFTER
# the process started (e.g. under `uvicorn --reload`, which only watches
# *.py files, never .env) would keep reporting the stale pre-.env state
# indefinitely -- while any fresh script/process correctly saw the current
# .env, because it's a brand new Settings() instance. Reproduced directly
# (see the conversation this fix came from) by starting a server with no
# live config, then editing .env in place without restarting: the old
# endpoint kept returning false forever; the fix below picks up the change
# on the very next request.
#
# Fix: data_source_status() now builds a fresh Settings() per call instead
# of reusing the startup-time singleton. is_configured() gained an optional
# `cfg` parameter (default: the existing singleton) so every OTHER caller
# is completely unaffected -- this is scoped to the one diagnostic endpoint
# whose entire job is "what is configured right now".
# ---------------------------------------------------------------------------

def test_is_configured_still_defaults_to_the_module_singleton():
    """Every pre-existing caller passes no argument at all -- must keep
    working exactly as before (same object, same result)."""
    from app.services import live_market_data
    from app.config import settings as singleton
    assert live_market_data.is_configured() == live_market_data.is_configured(singleton)


def test_is_configured_accepts_an_explicit_fresh_settings_object():
    from app.services import live_market_data
    from app.config import Settings

    unconfigured = Settings(data_gov_in_api_key="", market_data_source="demo")
    assert live_market_data.is_configured(unconfigured) is False

    configured = Settings(data_gov_in_api_key="a-real-looking-key", market_data_source="live")
    assert live_market_data.is_configured(configured) is True


def test_data_source_status_reflects_a_settings_change_without_needing_a_restart(monkeypatch):
    """
    The exact reported scenario: simulate a server process whose imported
    `settings` singleton was built BEFORE live data was configured (as if
    the process started before .env was finished), then simulate the
    operator finishing .env / setting the real environment variables
    afterwards -- all withOUT constructing a new process. The endpoint
    must reflect the new configuration on its very next call.
    """
    from app.config import settings as singleton

    # Simulate "process started before .env had live config": the
    # long-lived singleton is stuck on the old, unconfigured values.
    monkeypatch.setattr(singleton, "data_gov_in_api_key", "")
    monkeypatch.setattr(singleton, "market_data_source", "demo")

    # Simulate ".env was edited / real env vars were exported after the
    # process started" -- a FRESH Settings() (which data_source_status()
    # now constructs on every call) will pick these up; the stale
    # singleton above deliberately will not.
    monkeypatch.setenv("DATA_GOV_IN_API_KEY", "fake-test-key-12345")
    monkeypatch.setenv("MARKET_DATA_SOURCE", "live")

    result = market_router.data_source_status()

    assert result["live_data_configured"] is True, (
        "data-source-status must reflect the CURRENT environment, not a "
        "startup-time snapshot -- this is exactly the reported bug"
    )
    assert result["provider"] == "data.gov.in (Agmarknet)"

    # And prove the OLD, buggy behavior really would have been wrong: the
    # stale singleton alone still disagrees, confirming this test would
    # have failed against the pre-fix code path.
    assert singleton.market_data_source == "demo"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
