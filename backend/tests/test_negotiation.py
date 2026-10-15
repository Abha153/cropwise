import os
import sys

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import models, schemas
from app.database import Base
from app.routers import negotiations as nr
from app.routers import offers as offers_router


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture()
def world(db):
    farmer = models.Farmer(name="F", email="f@example.com", password_hash="x", location="Bilaspur")
    other_farmer = models.Farmer(name="F2", email="f2@example.com", password_hash="x", location="Durg")
    buyer = models.Buyer(company_name="B", email="b@example.com", password_hash="x", location="Raipur")
    other_buyer = models.Buyer(company_name="B2", email="b2@example.com", password_hash="x", location="Raipur")
    db.add_all([farmer, other_farmer, buyer, other_buyer])
    db.flush()
    lot = models.Lot(lot_number="LOT-NEG-1", farmer_id=farmer.id, crop="Tomato", quantity_kg=100,
                     location="Bilaspur", expected_price=30, grade="B", status="AVAILABLE")
    db.add(lot)
    db.commit()
    return dict(farmer=farmer, other_farmer=other_farmer, buyer=buyer, other_buyer=other_buyer, lot=lot)


def as_(role, user):
    return {"role": role, "user": user}


def make_offer(db, w, price=25.0, qty=40.0, **terms):
    return offers_router.create_offer(
        schemas.OfferCreate(lot_id=w["lot"].id, offered_price_per_kg=price, quantity_kg=qty, **terms),
        w["buyer"], db)


def counter(db, offer, who, **changes):
    return nr.counter_offer(offer.id, schemas.CounterOfferRequest(**changes), as_(*who), db)


def test_create_offer_starts_round_one_with_terms(db, world):
    offer = make_offer(db, world, pickup_mode="BUYER_PICKUP", pickup_date="2026-11-01", quality_grade="a")
    view = nr.get_negotiation(offer.id, as_("buyer", world["buyer"]), db)
    assert len(view["rounds"]) == 1
    r = view["rounds"][0]
    assert (r["proposed_by"], r["status"], r["price_per_kg"], r["quantity_kg"]) == ("buyer", "PROPOSED", 25.0, 40.0)
    assert r["pickup_mode"] == "BUYER_PICKUP" and r["quality_grade"] == "A"
    assert view["awaiting"] == "farmer"
    assert view["can"] == {"counter": False, "accept": False, "reject": False, "withdraw": True}


def test_round_one_defaults_quality_from_lot(db, world):
    offer = make_offer(db, world)
    assert nr.get_negotiation(offer.id, as_("farmer", world["farmer"]), db)["rounds"][0]["quality_grade"] == "B"


def test_full_negotiation_to_agreement_and_transaction(db, world):
    f, b = ("farmer", world["farmer"]), ("buyer", world["buyer"])
    offer = make_offer(db, world, price=25, qty=40)
    counter(db, offer, f, price_per_kg=30, pickup_mode="BUYER_PICKUP", pickup_date="2026-11-02",
            message="Pickup from my farm")
    counter(db, offer, b, price_per_kg=28, quantity_kg=50, delivery_deadline="2026-11-05")
    view = nr.accept_proposal(offer.id, as_(*f), db)

    assert [r["status"] for r in view["rounds"]] == ["COUNTERED", "COUNTERED", "ACCEPTED"]
    assert [r["proposed_by"] for r in view["rounds"]] == ["buyer", "farmer", "buyer"]
    txn = db.query(models.Transaction).one()
    assert (txn.final_price_per_kg, txn.quantity_kg, txn.total_amount) == (28, 50, 1400)
    assert txn.offer_id == offer.id and view["transaction_id"] == txn.id

    ag = db.query(models.NegotiationAgreement).one()
    assert ag.accepted_by == "farmer" and ag.rounds_count == 3 and ag.transaction_id == txn.id
    assert ag.terms["price_per_kg"] == 28 and ag.terms["pickup_mode"] == "BUYER_PICKUP"  # inherited from round 2
    assert ag.terms["delivery_deadline"] == "2026-11-05" and len(ag.terms_hash) == 64
    events = [e.event_type for e in txn.events]
    assert events == ["OFFER_CREATED", "OFFER_ACCEPTED", "AGREEMENT_RECORDED"]

    db.refresh(world["lot"])
    assert world["lot"].quantity_kg == 50 and world["lot"].status == "AVAILABLE"
    done = nr.negotiation_for_transaction(txn.id, as_(*b), db)
    assert done["agreement"]["terms_hash"] == ag.terms_hash and len(done["rounds"]) == 3


def test_buyer_can_accept_farmers_counter(db, world):
    offer = make_offer(db, world, price=25, qty=100)
    counter(db, offer, ("farmer", world["farmer"]), price_per_kg=31)
    view = nr.accept_proposal(offer.id, as_("buyer", world["buyer"]), db)
    txn = db.query(models.Transaction).one()
    assert txn.final_price_per_kg == 31 and txn.farmer_id == world["farmer"].id
    assert view["agreement"]["accepted_by"] == "buyer"
    db.refresh(world["lot"])
    assert world["lot"].status == "SOLD"
    assert db.query(models.Notification).filter_by(farmer_id=world["farmer"].id).count() >= 1


def test_turn_rules(db, world):
    offer = make_offer(db, world)
    with pytest.raises(HTTPException) as e:  # buyer can't counter their own proposal
        counter(db, offer, ("buyer", world["buyer"]), price_per_kg=26)
    assert e.value.status_code == 409
    counter(db, offer, ("farmer", world["farmer"]), price_per_kg=30)
    with pytest.raises(HTTPException) as e:  # farmer can't accept own counter (legacy endpoint)
        offers_router.accept_offer(offer.id, world["farmer"], db)
    assert e.value.status_code == 409
    with pytest.raises(HTTPException) as e:
        nr.accept_proposal(offer.id, as_("farmer", world["farmer"]), db)
    assert e.value.status_code == 409
    with pytest.raises(HTTPException) as e:  # farmer can't reject own counter either
        offers_router.reject_offer(offer.id, world["farmer"], db)
    assert e.value.status_code == 409


def test_reject_closes_negotiation_and_frees_lot(db, world):
    offer = make_offer(db, world)
    db.refresh(world["lot"])
    assert world["lot"].status == "UNDER_OFFER"
    counter(db, offer, ("farmer", world["farmer"]), price_per_kg=30)
    view = nr.reject_proposal(offer.id, as_("buyer", world["buyer"]), db)
    assert view["offer_status"] == "rejected" and view["rounds"][-1]["status"] == "REJECTED"
    assert view["awaiting"] is None and not any(view["can"].values())
    db.refresh(world["lot"])
    assert world["lot"].status == "AVAILABLE"
    with pytest.raises(HTTPException) as e:
        counter(db, offer, ("farmer", world["farmer"]), price_per_kg=29)
    assert e.value.status_code == 400


def test_withdraw_only_by_proposer(db, world):
    offer = make_offer(db, world)
    with pytest.raises(HTTPException) as e:
        nr.withdraw_proposal(offer.id, as_("farmer", world["farmer"]), db)
    assert e.value.status_code == 409
    view = nr.withdraw_proposal(offer.id, as_("buyer", world["buyer"]), db)
    assert view["offer_status"] == "withdrawn" and view["rounds"][-1]["status"] == "WITHDRAWN"
    db.refresh(world["lot"])
    assert world["lot"].status == "AVAILABLE"


@pytest.mark.parametrize("changes,code", [
    ({"quantity_kg": 500}, 400),                       # more than available
    ({"price_per_kg": 0}, 400),
    ({"quality_grade": "Z"}, 400),
    ({"pickup_mode": "TELEPORT"}, 400),
    ({"pickup_date": "02-11-2026"}, 400),
    ({"pickup_date": "2026-11-10", "delivery_deadline": "2026-11-01"}, 400),
    ({"price_per_kg": 25.0}, 400),                     # no change from current proposal
    ({"quality_notes": "x" * 501}, 400),
])
def test_counter_validation(db, world, changes, code):
    offer = make_offer(db, world, price=25, qty=40)
    with pytest.raises(HTTPException) as e:
        counter(db, offer, ("farmer", world["farmer"]), **changes)
    assert e.value.status_code == code
    assert len(nr.get_negotiation(offer.id, as_("farmer", world["farmer"]), db)["rounds"]) == 1


def test_only_parties_can_see_or_act(db, world):
    offer = make_offer(db, world)
    for who in (("farmer", world["other_farmer"]), ("buyer", world["other_buyer"])):
        with pytest.raises(HTTPException) as e:
            nr.get_negotiation(offer.id, as_(*who), db)
        assert e.value.status_code == 403
    with pytest.raises(HTTPException) as e:
        nr.get_negotiation(offer.id, as_("transporter", object()), db)
    assert e.value.status_code == 403


def test_legacy_offer_without_rounds_still_works(db, world):
    legacy = models.BuyerOffer(buyer_id=world["buyer"].id, lot_id=world["lot"].id,
                               offered_price_per_kg=27, quantity_kg=20, status="pending")
    db.add(legacy)
    world["lot"].status = "UNDER_OFFER"
    db.commit()
    assert db.query(models.NegotiationRound).count() == 0
    result = offers_router.accept_offer(legacy.id, world["farmer"], db)
    assert result["accepted"] is True
    rounds = db.query(models.NegotiationRound).all()
    assert len(rounds) == 1 and rounds[0].status == "ACCEPTED"
    assert db.query(models.NegotiationAgreement).one().terms["price_per_kg"] == 27


def test_accepting_one_offer_closes_rivals_when_lot_sells_out(db, world):
    first = make_offer(db, world, price=25, qty=100)
    rival = offers_router.create_offer(
        schemas.OfferCreate(lot_id=world["lot"].id, offered_price_per_kg=24, quantity_kg=100),
        world["other_buyer"], db)
    offers_router.accept_offer(first.id, world["farmer"], db)
    db.refresh(rival)
    assert rival.status == "rejected"
    last = db.query(models.NegotiationRound).filter_by(offer_id=rival.id).one()
    assert last.status == "REJECTED" and last.responded_by == "system"


def test_round_limit(db, world):
    offer = make_offer(db, world, price=25, qty=40)  # round 1, by the buyer
    farmer, buyer = ("farmer", world["farmer"]), ("buyer", world["buyer"])
    for round_no in range(2, 13):  # farmer proposes even rounds, buyer odd
        counter(db, offer, farmer if round_no % 2 == 0 else buyer, price_per_kg=25 + round_no)
    assert len(nr.get_negotiation(offer.id, as_(*buyer), db)["rounds"]) == 12
    with pytest.raises(HTTPException) as e:  # round 12 was the farmer's, so the buyer is up
        counter(db, offer, buyer, price_per_kg=99)
    assert e.value.status_code == 400 and "limit" in e.value.detail.lower()
    # accepting is still possible at the limit
    assert nr.accept_proposal(offer.id, as_(*buyer), db)["transaction_id"]
