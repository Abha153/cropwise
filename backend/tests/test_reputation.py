"""
Tests for partner reputation / QoS (buyers + transport agencies).

Covers the honesty rules: no invented values, "Insufficient history" for new
partners, small samples cannot outrank large ones, simulated payments are
excluded, and contested evidence is left out of the rates.

Run: pytest backend/tests/test_reputation.py -v
"""
import datetime as dt

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models
from app.database import Base
from app.services import reputation as rep

NOW = dt.datetime(2026, 10, 15, 12, 0, 0)


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    s = sessionmaker(bind=engine)()
    yield s
    s.close()


def _farmer(db, n=1):
    f = models.Farmer(name=f"F{n}", email=f"f{n}@x.in", password_hash="x", location="Bilaspur")
    db.add(f); db.flush(); return f


def _buyer(db, n=1, **kw):
    b = models.Buyer(company_name=f"B{n}", email=f"b{n}@x.in", password_hash="x", location="Raipur", **kw)
    db.add(b); db.flush(); return b


def _transporter(db, n=1):
    t = models.Transporter(name=f"T{n}", email=f"t{n}@x.in", password_hash="x")
    db.add(t); db.flush(); return t


def _trip(db, farmer, t, **kw):
    r = models.TransportRequest(farmer_id=farmer.id, transporter_id=t.id,
                                pickup_location="A", destination="B", **kw)
    db.add(r); db.flush(); return r


# ── pure helpers ─────────────────────────────────────────────────────────────
def test_wilson_small_perfect_sample_ranks_below_large_good_sample():
    assert rep.wilson_lower_bound(5, 5) < rep.wilson_lower_bound(95, 100)
    assert rep.wilson_lower_bound(0, 0) is None


def test_indicator_without_evidence_is_not_recorded_not_zero():
    ind = rep.indicator("x", "X", 0, 0)
    assert ind["status"] == "not_recorded" and ind["value"] is None and ind["denominator"] == 0


def test_pickup_schedule_uses_ist_and_grace():
    sched = rep.scheduled_pickup_utc("2026-10-10", "10:00")      # 10:00 IST = 04:30 UTC
    assert sched == dt.datetime(2026, 10, 10, 4, 30)
    assert rep.pickup_on_time(sched, dt.datetime(2026, 10, 10, 6, 0)) is True
    assert rep.pickup_on_time(sched, dt.datetime(2026, 10, 10, 7, 0)) is False
    assert rep.pickup_on_time(None, dt.datetime(2026, 10, 10, 6, 0)) is None
    assert rep.scheduled_pickup_utc("not-a-date", None) is None


def test_quote_accuracy_only_penalises_overcharge():
    assert rep.quote_deviation_pct(1000, 1040) == 4.0 and rep.quote_accurate(4.0) is True
    assert rep.quote_accurate(rep.quote_deviation_pct(1000, 1200)) is False
    assert rep.quote_accurate(rep.quote_deviation_pct(1000, 900)) is True
    assert rep.quote_deviation_pct(None, 900) is None and rep.quote_deviation_pct(0, 900) is None


# ── transporter profile ──────────────────────────────────────────────────────
def test_new_transporter_is_insufficient_history_with_no_invented_numbers(db):
    t = _transporter(db); db.commit()
    p = rep.transporter_profile(db, t.id, NOW)
    assert p["label"] == rep.LABEL_INSUFFICIENT and p["sufficient_history"] is False
    assert all(i["status"] == "not_recorded" and i["value"] is None for i in p["indicators"])
    assert p["ranking"]["eligible"] is False and p["ranking"]["wilson_lower_bound"] is None
    assert p["farmer_feedback"]["average_overall"] is None


def test_transporter_rates_come_from_recorded_rows(db):
    f, t = _farmer(db), _transporter(db)
    for i in range(4):   # four delivered trips, 3 on time, 1 late
        late = (i == 3)
        _trip(db, f, t, status="DELIVERED", pickup_date="2026-10-01", pickup_time="10:00",
              picked_up_at=dt.datetime(2026, 10, 1, 9, 0) if late else dt.datetime(2026, 10, 1, 4, 30),
              delivered_at=dt.datetime(2026, 10, 2), transporter_agreed_price=1000,
              final_charge=1000 if i < 3 else 1300, final_charge_recorded_at=dt.datetime(2026, 10, 3))
    _trip(db, f, t, status="CANCELLED", cancelled_by="transporter", cancelled_at=dt.datetime(2026, 10, 5))
    _trip(db, f, t, status="CANCELLED", cancelled_by="farmer")
    _trip(db, f, t, status="CANCELLED")                      # legacy: cause not recorded
    db.commit()
    p = rep.transporter_profile(db, t.id, NOW)
    ind = {i["key"]: i for i in p["indicators"]}
    assert p["label"] == rep.LABEL_ESTABLISHED
    assert (ind["on_time_pickup"]["numerator"], ind["on_time_pickup"]["denominator"]) == (3, 4)
    assert (ind["quote_accuracy"]["numerator"], ind["quote_accuracy"]["denominator"]) == (3, 4)
    assert (ind["trip_fulfilment"]["numerator"], ind["trip_fulfilment"]["denominator"]) == (4, 5)
    assert ind["on_time_delivery"]["status"] == "not_recorded"        # no delivery promise recorded
    assert p["trip_history"]["cancelled_by_agency"] == 1
    assert p["trip_history"]["cancelled_other_or_unrecorded"] == 2     # not counted against the agency


def test_delivery_promise_is_used_only_when_recorded(db):
    f, t = _farmer(db), _transporter(db)
    _trip(db, f, t, status="DELIVERED", delivered_at=dt.datetime(2026, 10, 2, 6, 0), promised_delivery_by="2026-10-02")
    _trip(db, f, t, status="DELIVERED", delivered_at=dt.datetime(2026, 10, 4, 6, 0), promised_delivery_by="2026-10-02")
    _trip(db, f, t, status="DELIVERED", delivered_at=dt.datetime(2026, 10, 4, 6, 0))        # no promise
    db.commit()
    ind = {i["key"]: i for i in rep.transporter_profile(db, t.id, NOW)["indicators"]}
    assert (ind["on_time_delivery"]["numerator"], ind["on_time_delivery"]["denominator"]) == (1, 2)


def test_contested_trip_is_excluded_from_rates_while_open_and_after_upheld_but_not_when_rejected(db):
    f, t = _farmer(db), _transporter(db)
    trips = [_trip(db, f, t, status="DELIVERED", transporter_agreed_price=1000,
                   final_charge=1000 if i < 3 else 2000, final_charge_recorded_at=NOW) for i in range(4)]
    d = models.ReputationDispute(subject_role="transporter", subject_id=t.id, target_type="TRANSPORT_REQUEST",
                                 target_id=trips[3].id, reason="Charge included a toll agreed verbally", status="OPEN")
    db.add(d); db.commit()
    q = lambda: {i["key"]: i for i in rep.transporter_profile(db, t.id, NOW)["indicators"]}["quote_accuracy"]
    assert (q()["numerator"], q()["denominator"]) == (3, 3)
    assert rep.transporter_profile(db, t.id, NOW)["trip_history"]["contested_items_under_review"] == 1
    d.status = "UPHELD"; db.commit()
    assert q()["denominator"] == 3
    d.status = "REJECTED"; db.commit()
    assert (q()["numerator"], q()["denominator"]) == (3, 4)


def test_open_complaints_are_counted_but_not_treated_as_findings(db):
    t, f = _transporter(db), _farmer(db)
    db.add(models.Grievance(raised_by="farmer", raised_by_id=f.id, against_user="transporter",
                            against_user_id=t.id, category="DELIVERY", description="Late", status="OPEN"))
    db.commit()
    c = rep.transporter_profile(db, t.id, NOW)["complaints_and_disputes"]
    assert c["recorded"] == 1 and c["pending_review"] == 1 and c["dismissed"] == 0


# ── buyer profile ────────────────────────────────────────────────────────────
def test_buyer_seeded_reliability_columns_are_never_used(db):
    b = _buyer(db, reliability_score=99.0, payment_history_score=99.0); db.commit()
    p = rep.buyer_profile(db, b.id, NOW)
    assert p["label"] == rep.LABEL_INSUFFICIENT
    assert all(i["value"] is None for i in p["indicators"])
    assert "99" not in str(p)


def _txn(db, f, b, status="COMPLETED"):
    t = models.Transaction(farmer_id=f.id, buyer_id=b.id, final_price_per_kg=20, quantity_kg=100,
                           total_amount=2000, status=status, updated_at=NOW)
    db.add(t); db.flush(); return t


def test_buyer_indicators_from_farmer_recorded_outcomes(db):
    f, b = _farmer(db), _buyer(db)
    txns = [_txn(db, f, b) for _ in range(4)] + [_txn(db, f, b, "IN_TRANSIT"), _txn(db, f, b, "CANCELLED")]
    for i, t in enumerate(txns[:4]):
        db.add(models.PerformanceRecord(subject_role="buyer", subject_id=b.id, transaction_id=t.id,
                                        metric="BUYER_PICKUP", result="ON_TIME" if i < 3 else "NO_SHOW",
                                        recorded_by_role="farmer", recorded_by_id=f.id, created_at=NOW))
    db.commit()
    p = rep.buyer_profile(db, b.id, NOW)
    ind = {i["key"]: i for i in p["indicators"]}
    assert p["transaction_history"] == {**p["transaction_history"], "completed": 4, "cancelled": 1, "in_progress": 1}
    assert (ind["pickup_reliability"]["numerator"], ind["pickup_reliability"]["denominator"]) == (3, 4)
    assert ind["terms_adherence"]["status"] == "not_recorded"
    assert p["label"] == rep.LABEL_ESTABLISHED


def test_simulated_payments_are_excluded_from_payment_indicator(db):
    f, b = _farmer(db), _buyer(db)
    t = _txn(db, f, b)
    db.add(models.Payment(transaction_id=t.id, buyer_id=b.id, farmer_id=f.id, amount=2000,
                          payment_status="PAID", is_demo=True, received_at=NOW)); db.commit()
    pay = {i["key"]: i for i in rep.buyer_profile(db, b.id, NOW)["indicators"]}["payment_status"]
    assert pay["status"] == "not_recorded" and pay["simulated_payments_excluded"] == 1
    assert "simulated" in pay["detail"].lower()


def test_real_payments_paid_on_time_vs_late(db):
    f, b = _farmer(db), _buyer(db)
    for due, got in [("2026-10-05", dt.datetime(2026, 10, 4)), ("2026-10-05", dt.datetime(2026, 10, 9))]:
        t = _txn(db, f, b)
        db.add(models.Payment(transaction_id=t.id, buyer_id=b.id, farmer_id=f.id, amount=2000, payment_status="PAID",
                              is_demo=False, payment_due_date=due, received_at=got))
    db.commit()
    pay = {i["key"]: i for i in rep.buyer_profile(db, b.id, NOW)["indicators"]}["payment_status"]
    assert (pay["numerator"], pay["denominator"]) == (1, 2)


# ── ranking ──────────────────────────────────────────────────────────────────
def test_ranking_puts_established_first_and_leaves_new_partners_unranked(db):
    f = _farmer(db)
    big, small, new = _transporter(db, 1), _transporter(db, 2), _transporter(db, 3)
    for _ in range(100):
        _trip(db, f, big, status="DELIVERED")
    for _ in range(4):
        _trip(db, f, small, status="DELIVERED")
    db.commit()
    ranked = rep.rank_profiles([rep.transporter_profile(db, x.id, NOW) for x in (new, small, big)])
    assert [p["partner_id"] for p in ranked] == [big.id, small.id, new.id]
    assert [p["ranking"]["position"] for p in ranked] == [1, 2, None]


# ── API smoke: routes registered, auth enforced, methodology public ──────────
def test_routes_registered_and_protected():
    from fastapi.testclient import TestClient
    from app.main import app
    c = TestClient(app)
    paths = {r.path for r in app.routes}
    for p in ("/reputation/methodology", "/reputation/transporters", "/reputation/buyers",
              "/reputation/records", "/reputation/disputes", "/reputation/admin/disputes/{dispute_id}"):
        assert p in paths
    assert c.get("/reputation/methodology").status_code == 200
    assert c.get("/reputation/buyers").status_code == 401            # profiles need a login
    assert c.post("/reputation/records", json={}).status_code == 401
