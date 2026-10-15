"""
Negotiation workflow between a farmer and a buyer, on top of BuyerOffer.

    Offer -> Counteroffer -> Accept / Reject -> Agreement -> Transaction record

* Round 1 is the buyer's original offer. Every counteroffer is a new
  NegotiationRound proposed by the other party; terms inherit from the
  previous round unless changed, and every round stores the complete terms.
* Only the party who did NOT make the open proposal may counter, accept or
  reject it. The proposer may withdraw it. There is never more than one open
  (PROPOSED) round per offer.
* BuyerOffer.offered_price_per_kg / quantity_kg always mirror the CURRENT
  open proposal, so the existing accept/reject endpoints and every screen
  that lists offers keep working. The full history lives in the rounds.
* Accepting creates a NegotiationAgreement (terms snapshot + SHA-256 of the
  canonical terms) in the same database transaction as the Transaction.

Offers created before this feature have no rounds; ensure_rounds() lazily
creates round 1 from the offer row, so nothing needs migrating.
"""
import datetime as dt
import hashlib
import json
from typing import Dict, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import models

MAX_ROUNDS = 12
PICKUP_MODES = ("BUYER_PICKUP", "FARMER_DELIVERY", "TO_BE_AGREED")
QUALITY_GRADES = ("A", "B", "C")
TERM_FIELDS = (
    "price_per_kg", "quantity_kg", "quality_grade", "quality_notes",
    "pickup_mode", "pickup_date", "delivery_location", "delivery_deadline",
)
OPEN = "PROPOSED"


def _now():
    return dt.datetime.utcnow()


def other_party(role: str) -> str:
    return "farmer" if role == "buyer" else "buyer"


# ---------- who owns what ----------

def offer_target(db: Session, offer: models.BuyerOffer):
    """(farmer_id, available_quantity_kg, default_quality_grade, location) of the lot/listing."""
    if offer.listing_id:
        listing = db.query(models.CropListing).filter(models.CropListing.id == offer.listing_id).first()
        if listing:
            return listing.farmer_id, listing.quantity_kg, listing.quality_grade, listing.location
    elif offer.lot_id:
        lot = db.query(models.Lot).filter(models.Lot.id == offer.lot_id).first()
        if lot:
            return lot.farmer_id, lot.quantity_kg, lot.grade, lot.location
    raise HTTPException(status_code=404, detail="The lot or listing for this offer no longer exists")


def actor_role(db: Session, offer: models.BuyerOffer, current: dict) -> str:
    """'buyer' or 'farmer' if the signed-in user is a party to this offer, else 403."""
    role, user = current["role"], current["user"]
    if role == "buyer" and user.id == offer.buyer_id:
        return "buyer"
    if role == "farmer" and user.id == offer_target(db, offer)[0]:
        return "farmer"
    raise HTTPException(status_code=403, detail="You are not a party to this negotiation")


# ---------- rounds ----------

def round_terms(r: models.NegotiationRound) -> Dict:
    return {f: getattr(r, f) for f in TERM_FIELDS}


def rounds_for(db: Session, offer_id: int):
    return (
        db.query(models.NegotiationRound)
        .filter(models.NegotiationRound.offer_id == offer_id)
        .order_by(models.NegotiationRound.round_no)
        .all()
    )


def ensure_rounds(db: Session, offer: models.BuyerOffer):
    """Create round 1 from the offer row if this offer predates negotiations."""
    existing = rounds_for(db, offer.id)
    if existing:
        return existing
    _, _, default_grade, _ = offer_target(db, offer)
    status = {"pending": OPEN, "accepted": "ACCEPTED", "rejected": "REJECTED",
              "withdrawn": "WITHDRAWN"}.get(offer.status, OPEN)
    first = models.NegotiationRound(
        offer_id=offer.id, round_no=1, proposed_by="buyer", proposed_by_id=offer.buyer_id,
        price_per_kg=offer.offered_price_per_kg, quantity_kg=offer.quantity_kg,
        quality_grade=default_grade, message=offer.message or None, status=status,
        created_at=offer.created_at or _now(),
    )
    db.add(first)
    db.flush()
    return [first]


def open_round(db: Session, offer: models.BuyerOffer) -> Optional[models.NegotiationRound]:
    return (
        db.query(models.NegotiationRound)
        .filter(models.NegotiationRound.offer_id == offer.id, models.NegotiationRound.status == OPEN)
        .order_by(models.NegotiationRound.round_no.desc())
        .first()
    )


def require_open_round(db: Session, offer: models.BuyerOffer) -> models.NegotiationRound:
    ensure_rounds(db, offer)
    if offer.status != "pending":
        raise HTTPException(status_code=400, detail=f"This negotiation is closed (offer {offer.status})")
    rnd = open_round(db, offer)
    if rnd is None:
        raise HTTPException(status_code=400, detail="There is no open proposal to respond to")
    return rnd


def require_turn(rnd: models.NegotiationRound, role: str):
    if rnd.proposed_by == role:
        raise HTTPException(
            status_code=409,
            detail="Waiting for the other party: you can't respond to your own proposal (you can withdraw it)",
        )


# ---------- validation ----------

def _clean_text(value: Optional[str], limit: int) -> Optional[str]:
    if value is None:
        return None
    value = value.strip()
    if len(value) > limit:
        raise HTTPException(status_code=400, detail=f"Text is too long (max {limit} characters)")
    return value or None


def _check_date(value: Optional[str], label: str) -> Optional[str]:
    if value in (None, ""):
        return None
    try:
        return dt.date.fromisoformat(value).isoformat()
    except ValueError:
        raise HTTPException(status_code=400, detail=f"{label} must be a date in YYYY-MM-DD format")


def merge_terms(previous: Dict, changes: Dict, available_qty: float) -> Dict:
    """Previous round's terms overlaid with the fields the caller actually sent
    (None = not sent). Validates the result."""
    terms = dict(previous)
    for key in TERM_FIELDS:
        if changes.get(key) is not None:
            terms[key] = changes[key]

    if terms["price_per_kg"] is None or float(terms["price_per_kg"]) <= 0:
        raise HTTPException(status_code=400, detail="Price must be greater than zero")
    if terms["quantity_kg"] is None or float(terms["quantity_kg"]) <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be greater than zero")
    terms["price_per_kg"] = round(float(terms["price_per_kg"]), 2)
    terms["quantity_kg"] = round(float(terms["quantity_kg"]), 2)
    if terms["quantity_kg"] > available_qty:
        raise HTTPException(
            status_code=400,
            detail=f"Quantity ({terms['quantity_kg']} kg) exceeds the available quantity ({available_qty} kg)",
        )

    grade = terms.get("quality_grade")
    if grade is not None:
        grade = str(grade).upper()
        if grade not in QUALITY_GRADES:
            raise HTTPException(status_code=400, detail="Quality grade must be A, B or C")
    terms["quality_grade"] = grade

    mode = terms.get("pickup_mode")
    if mode is not None and mode not in PICKUP_MODES:
        raise HTTPException(status_code=400, detail=f"Pickup mode must be one of {', '.join(PICKUP_MODES)}")

    terms["quality_notes"] = _clean_text(terms.get("quality_notes"), 500)
    terms["delivery_location"] = _clean_text(terms.get("delivery_location"), 200)
    terms["pickup_date"] = _check_date(terms.get("pickup_date"), "Pickup date")
    terms["delivery_deadline"] = _check_date(terms.get("delivery_deadline"), "Delivery deadline")
    if terms["pickup_date"] and terms["delivery_deadline"] and terms["delivery_deadline"] < terms["pickup_date"]:
        raise HTTPException(status_code=400, detail="Delivery deadline can't be before the pickup date")
    return terms


# ---------- actions ----------

def add_counter(db: Session, offer: models.BuyerOffer, role: str, actor_id: int,
                changes: Dict, message: Optional[str]) -> models.NegotiationRound:
    current = require_open_round(db, offer)
    require_turn(current, role)
    rounds = rounds_for(db, offer.id)
    if len(rounds) >= MAX_ROUNDS:
        raise HTTPException(status_code=400, detail=f"Negotiation limit reached ({MAX_ROUNDS} rounds). Accept or reject.")

    _, available, _, _ = offer_target(db, offer)
    terms = merge_terms(round_terms(current), changes, available)
    if all(terms[f] == getattr(current, f) for f in TERM_FIELDS):
        raise HTTPException(status_code=400, detail="A counteroffer must change at least one term")

    current.status = "COUNTERED"
    current.responded_at = _now()
    current.responded_by = role
    new = models.NegotiationRound(
        offer_id=offer.id, round_no=current.round_no + 1, proposed_by=role, proposed_by_id=actor_id,
        message=_clean_text(message, 500), status=OPEN, **terms,
    )
    db.add(new)
    # Keep the offer row in step with the live proposal (see module docstring).
    offer.offered_price_per_kg = new.price_per_kg
    offer.quantity_kg = new.quantity_kg
    db.flush()
    return new


def close_round(rnd: models.NegotiationRound, status: str, role: str):
    rnd.status = status
    rnd.responded_at = _now()
    rnd.responded_by = role


def _canonical_hash(terms: Dict) -> str:
    return hashlib.sha256(json.dumps(terms, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def record_agreement(db: Session, offer: models.BuyerOffer, transaction: models.Transaction,
                     accepted_by: str) -> models.NegotiationAgreement:
    """Mark the open round accepted and write the agreement + a timeline event.
    Must run in the same db transaction that created `transaction`."""
    rounds = ensure_rounds(db, offer)
    rnd = open_round(db, offer) or rounds[-1]
    close_round(rnd, "ACCEPTED", accepted_by)

    terms = round_terms(rnd)
    agreement = models.NegotiationAgreement(
        offer_id=offer.id, transaction_id=transaction.id, round_id=rnd.id,
        farmer_id=transaction.farmer_id, buyer_id=transaction.buyer_id,
        accepted_by=accepted_by, terms=terms, terms_hash=_canonical_hash(terms),
        rounds_count=len(rounds),
    )
    db.add(agreement)
    db.add(models.TransactionEvent(
        transaction_id=transaction.id, event_type="AGREEMENT_RECORDED",
        description=(f"Terms agreed after {len(rounds)} round(s): ₹{terms['price_per_kg']}/kg × "
                     f"{terms['quantity_kg']} kg. Accepted by {accepted_by}."),
        performed_by=accepted_by,
        performed_by_id=transaction.farmer_id if accepted_by == "farmer" else transaction.buyer_id,
        event_metadata={"terms_hash": agreement.terms_hash, "rounds": len(rounds), "offer_id": offer.id},
    ))
    return agreement


def notify(db: Session, to_role: str, farmer_id: int, buyer_id: int, title: str, message: str,
           severity: str = "info"):
    db.add(models.Notification(
        farmer_id=farmer_id if to_role == "farmer" else None,
        buyer_id=buyer_id if to_role == "buyer" else None,
        type="NEGOTIATION", title=title, message=message, severity=severity,
    ))


def round_out(r: models.NegotiationRound) -> Dict:
    return {
        "id": r.id, "round_no": r.round_no, "proposed_by": r.proposed_by, "status": r.status,
        "message": r.message, "created_at": r.created_at, "responded_at": r.responded_at,
        "responded_by": r.responded_by, **round_terms(r),
    }


def agreement_out(a: Optional[models.NegotiationAgreement]) -> Optional[Dict]:
    if a is None:
        return None
    return {
        "id": a.id, "offer_id": a.offer_id, "transaction_id": a.transaction_id, "accepted_by": a.accepted_by,
        "terms": a.terms, "terms_hash": a.terms_hash, "rounds_count": a.rounds_count, "agreed_at": a.agreed_at,
    }
