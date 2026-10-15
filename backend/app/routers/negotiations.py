"""
Negotiation endpoints -- Offer -> Counteroffer -> Accept / Reject -> Agreement
-> Transaction record. See app/services/negotiation_service.py for the rules.

Both the farmer who owns the lot/listing and the buyer who made the offer
can use these; anyone else gets 403.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth_utils import get_current_user
from app.database import get_db
from app.routers import offers as offers_router
from app.services import negotiation_service as neg

router = APIRouter(prefix="/negotiations", tags=["negotiations"])


def _get_offer(db: Session, offer_id: int) -> models.BuyerOffer:
    offer = db.query(models.BuyerOffer).filter(models.BuyerOffer.id == offer_id).first()
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    return offer


def _target_summary(db: Session, offer: models.BuyerOffer) -> dict:
    if offer.listing_id:
        t = db.query(models.CropListing).filter(models.CropListing.id == offer.listing_id).first()
        return {"type": "listing", "id": offer.listing_id, "crop": t.crop if t else None,
                "location": t.location if t else None, "available_kg": t.quantity_kg if t else None,
                "grade": t.quality_grade if t else None}
    t = db.query(models.Lot).filter(models.Lot.id == offer.lot_id).first()
    return {"type": "lot", "id": offer.lot_id, "crop": t.crop if t else None,
            "location": t.location if t else None, "available_kg": t.quantity_kg if t else None,
            "grade": t.grade if t else None}


def _view(db: Session, offer: models.BuyerOffer, role: str) -> dict:
    rounds = neg.ensure_rounds(db, offer)
    db.commit()  # persist round 1 for offers that predate negotiations
    agreement = (
        db.query(models.NegotiationAgreement).filter(models.NegotiationAgreement.offer_id == offer.id).first()
    )
    open_round = neg.open_round(db, offer) if offer.status == "pending" else None
    my_turn = role in ("buyer", "farmer") and open_round is not None and open_round.proposed_by != role
    return {
        "offer_id": offer.id,
        "offer_status": offer.status,
        "buyer_id": offer.buyer_id,
        "target": _target_summary(db, offer),
        "viewer_role": role,
        "awaiting": neg.other_party(open_round.proposed_by) if open_round else None,
        "can": {
            "counter": my_turn and len(rounds) < neg.MAX_ROUNDS,
            "accept": my_turn,
            "reject": my_turn,
            "withdraw": role in ("buyer", "farmer") and open_round is not None and open_round.proposed_by == role,
        },
        "max_rounds": neg.MAX_ROUNDS,
        "rounds": [neg.round_out(r) for r in neg.rounds_for(db, offer.id)],
        "agreement": neg.agreement_out(agreement),
        "transaction_id": agreement.transaction_id if agreement else None,
    }


@router.get("/offer/{offer_id}")
def get_negotiation(offer_id: int, current=Depends(get_current_user), db: Session = Depends(get_db)):
    offer = _get_offer(db, offer_id)
    role = neg.actor_role(db, offer, current)
    return _view(db, offer, role)


@router.post("/offer/{offer_id}/counter")
def counter_offer(offer_id: int, payload: schemas.CounterOfferRequest,
                  current=Depends(get_current_user), db: Session = Depends(get_db)):
    offer = _get_offer(db, offer_id)
    role = neg.actor_role(db, offer, current)
    changes = payload.model_dump(exclude={"message"})
    new = neg.add_counter(db, offer, role, current["user"].id, changes, payload.message)
    farmer_id = neg.offer_target(db, offer)[0]
    neg.notify(db, neg.other_party(role), farmer_id, offer.buyer_id, "New counteroffer",
               f"The {role} proposed ₹{new.price_per_kg}/kg for {new.quantity_kg} kg. Review and respond.")
    db.commit()
    return _view(db, offer, role)


@router.post("/offer/{offer_id}/accept")
def accept_proposal(offer_id: int, current=Depends(get_current_user), db: Session = Depends(get_db)):
    offer = _get_offer(db, offer_id)
    role = neg.actor_role(db, offer, current)
    farmer_id = neg.offer_target(db, offer)[0]
    farmer = current["user"] if role == "farmer" else (
        db.query(models.Farmer).filter(models.Farmer.id == farmer_id).first())
    result = offers_router.accept_offer_core(db, offer, farmer, accepted_by=role)
    view = _view(db, offer, role)
    view["transaction_id"] = result["transaction_id"]
    return view


@router.post("/offer/{offer_id}/reject")
def reject_proposal(offer_id: int, current=Depends(get_current_user), db: Session = Depends(get_db)):
    offer = _get_offer(db, offer_id)
    role = neg.actor_role(db, offer, current)
    offers_router.reject_offer_core(db, offer, role)
    farmer_id = neg.offer_target(db, offer)[0]
    neg.notify(db, neg.other_party(role), farmer_id, offer.buyer_id, "Proposal rejected",
               f"The {role} rejected the latest proposal. The negotiation is closed.", "warning")
    db.commit()
    return _view(db, offer, role)


@router.post("/offer/{offer_id}/withdraw")
def withdraw_proposal(offer_id: int, current=Depends(get_current_user), db: Session = Depends(get_db)):
    offer = _get_offer(db, offer_id)
    role = neg.actor_role(db, offer, current)
    open_round = neg.require_open_round(db, offer)
    if open_round.proposed_by != role:
        raise HTTPException(status_code=409, detail="You can only withdraw your own open proposal")
    offers_router.close_offer(db, offer, "withdrawn", role)
    farmer_id = neg.offer_target(db, offer)[0]
    neg.notify(db, neg.other_party(role), farmer_id, offer.buyer_id, "Proposal withdrawn",
               f"The {role} withdrew their proposal. The negotiation is closed.", "info")
    db.commit()
    return _view(db, offer, role)


@router.get("/transaction/{transaction_id}")
def negotiation_for_transaction(transaction_id: int, current=Depends(get_current_user),
                                db: Session = Depends(get_db)):
    """The agreed terms and full round history behind a transaction."""
    txn = db.query(models.Transaction).filter(models.Transaction.id == transaction_id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    role, user = current["role"], current["user"]
    is_party = (role == "farmer" and user.id == txn.farmer_id) or (role == "buyer" and user.id == txn.buyer_id)
    if not is_party and role != "admin":
        raise HTTPException(status_code=403, detail="You are not a party to this transaction")
    if not txn.offer_id:
        return {"transaction_id": txn.id, "agreement": None, "rounds": []}
    offer = _get_offer(db, txn.offer_id)
    view = _view(db, offer, role if is_party else "admin")
    return {"transaction_id": txn.id, "agreement": view["agreement"], "rounds": view["rounds"]}
