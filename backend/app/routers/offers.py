from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.auth_utils import require_buyer, require_farmer
from app.services import negotiation_service as neg

router = APIRouter(prefix="/offers", tags=["offers"])


@router.post("", response_model=schemas.OfferOut)
def create_offer(payload: schemas.OfferCreate, buyer: models.Buyer = Depends(require_buyer),
                  db: Session = Depends(get_db)):
    if bool(payload.listing_id) == bool(payload.lot_id):
        raise HTTPException(status_code=400, detail="Provide exactly one of listing_id or lot_id")

    if payload.offered_price_per_kg <= 0:
        raise HTTPException(status_code=400, detail="Offer price must be greater than zero")
    if payload.quantity_kg <= 0:
        raise HTTPException(status_code=400, detail="Offer quantity must be greater than zero")

    demand = None
    if payload.buyer_demand_id:
        demand = db.query(models.BuyerDemand).filter(
            models.BuyerDemand.id == payload.buyer_demand_id
        ).first()
        if not demand or demand.buyer_id != buyer.id:
            raise HTTPException(status_code=403, detail="You can only reference your own buyer demand")

    if payload.listing_id:
        listing = db.query(models.CropListing).filter(models.CropListing.id == payload.listing_id).first()
        if not listing:
            raise HTTPException(status_code=404, detail="Listing not found")
        if listing.status != "active":
            raise HTTPException(status_code=400, detail="This listing is no longer active")
        if payload.quantity_kg > listing.quantity_kg:
            raise HTTPException(
                status_code=400,
                detail=f"Offer quantity ({payload.quantity_kg} kg) exceeds the listed quantity ({listing.quantity_kg} kg)",
            )
        if listing.min_acceptable_price is not None and payload.offered_price_per_kg < listing.min_acceptable_price:
            raise HTTPException(
                status_code=400,
                detail=f"Offer is below the farmer's minimum acceptable price of \u20b9{listing.min_acceptable_price}/kg",
            )
        offer = models.BuyerOffer(
            buyer_id=buyer.id, listing_id=payload.listing_id,
            buyer_demand_id=payload.buyer_demand_id,
            offered_price_per_kg=payload.offered_price_per_kg,
            quantity_kg=payload.quantity_kg, message=payload.message or "",
            language=payload.language,
        )
    else:
        lot = db.query(models.Lot).filter(models.Lot.id == payload.lot_id).first()
        if not lot:
            raise HTTPException(status_code=404, detail="Lot not found")
        if lot.status not in ("AVAILABLE", "UNDER_OFFER"):
            raise HTTPException(status_code=400, detail=f"This lot is {lot.status} and cannot receive new offers")
        if payload.quantity_kg > lot.quantity_kg:
            raise HTTPException(
                status_code=400,
                detail=f"Offer quantity ({payload.quantity_kg} kg) exceeds the lot quantity ({lot.quantity_kg} kg)",
            )
        if lot.minimum_price is not None and payload.offered_price_per_kg < lot.minimum_price:
            raise HTTPException(
                status_code=400,
                detail=f"Offer is below the farmer's minimum acceptable price of \u20b9{lot.minimum_price}/kg",
            )
        offer = models.BuyerOffer(
            buyer_id=buyer.id, lot_id=payload.lot_id,
            buyer_demand_id=payload.buyer_demand_id,
            offered_price_per_kg=payload.offered_price_per_kg,
            quantity_kg=payload.quantity_kg, message=payload.message or "",
            language=payload.language,
        )
        lot.status = "UNDER_OFFER"

    db.add(offer)
    db.flush()
    # Round 1 of the negotiation = this offer, plus any terms the buyer sent.
    first = neg.ensure_rounds(db, offer)[0]
    initial = {k: getattr(payload, k) for k in neg.TERM_FIELDS if k not in ("price_per_kg", "quantity_kg")}
    if any(v is not None for v in initial.values()):
        _, available, _, _ = neg.offer_target(db, offer)
        terms = neg.merge_terms(neg.round_terms(first), initial, available)
        for k, v in terms.items():
            setattr(first, k, v)
    db.commit()
    db.refresh(offer)
    return offer


@router.get("/listing/{listing_id}", response_model=List[schemas.OfferOut])
def offers_for_listing(listing_id: int, farmer: models.Farmer = Depends(require_farmer),
                        db: Session = Depends(get_db)):
    listing = db.query(models.CropListing).filter(models.CropListing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing.farmer_id != farmer.id:
        raise HTTPException(status_code=403, detail="You can only view offers on your own listings")
    offers = (
        db.query(models.BuyerOffer)
        .filter(models.BuyerOffer.listing_id == listing_id)
        .order_by(models.BuyerOffer.offered_price_per_kg.desc())
        .all()
    )
    return offers


@router.get("/lot/{lot_id}", response_model=List[schemas.OfferOut])
def offers_for_lot(lot_id: int, farmer: models.Farmer = Depends(require_farmer),
                    db: Session = Depends(get_db)):
    lot = db.query(models.Lot).filter(models.Lot.id == lot_id).first()
    if not lot:
        raise HTTPException(status_code=404, detail="Lot not found")
    if lot.farmer_id != farmer.id:
        raise HTTPException(status_code=403, detail="You can only view offers on your own lots")
    offers = (
        db.query(models.BuyerOffer)
        .filter(models.BuyerOffer.lot_id == lot_id)
        .order_by(models.BuyerOffer.offered_price_per_kg.desc())
        .all()
    )
    return offers


@router.get("/mine", response_model=List[schemas.OfferOut])
def my_offers(buyer: models.Buyer = Depends(require_buyer), db: Session = Depends(get_db)):
    return (
        db.query(models.BuyerOffer)
        .filter(models.BuyerOffer.buyer_id == buyer.id)
        .order_by(models.BuyerOffer.created_at.desc())
        .all()
    )


@router.patch("/{offer_id}/accept")
def accept_offer(offer_id: int, farmer: models.Farmer = Depends(require_farmer),
                  db: Session = Depends(get_db)):
    offer = db.query(models.BuyerOffer).filter(models.BuyerOffer.id == offer_id).first()
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    if offer.status != "pending":
        raise HTTPException(status_code=400, detail=f"This offer is already {offer.status} and cannot be changed")
    return accept_offer_core(db, offer, farmer, accepted_by="farmer")


def accept_offer_core(db: Session, offer: models.BuyerOffer, farmer: models.Farmer, accepted_by: str):
    """Turn the offer's current open proposal into a Transaction + Agreement.
    `farmer` is the owner of the lot/listing (also used for the ownership
    checks); `accepted_by` is the party who actually accepted ('farmer'
    or 'buyer' -- the buyer accepts a farmer's counteroffer)."""
    # Only the party who did not make the open proposal may accept it.
    neg.require_turn(neg.require_open_round(db, offer), accepted_by)

    if offer.listing_id:
        listing = db.query(models.CropListing).filter(models.CropListing.id == offer.listing_id).first()
        if not listing or listing.farmer_id != farmer.id:
            raise HTTPException(status_code=403, detail="You can only accept offers on your own listings")
        if listing.status != "active":
            raise HTTPException(status_code=400, detail="This listing is no longer active")
        if offer.quantity_kg > listing.quantity_kg:
            raise HTTPException(status_code=400, detail="Offer quantity exceeds the remaining listing quantity")

        listing.quantity_kg = round(listing.quantity_kg - offer.quantity_kg, 2)
        listing.status = "sold" if listing.quantity_kg <= 0 else "active"
        others = []
        if listing.status == "sold":
            others = (
                db.query(models.BuyerOffer)
                .filter(models.BuyerOffer.listing_id == listing.id, models.BuyerOffer.id != offer.id,
                        models.BuyerOffer.status == "pending")
                .all()
            )
        market_used = listing.location
        lot_id = None
    else:
        lot = db.query(models.Lot).filter(models.Lot.id == offer.lot_id).first()
        if not lot or lot.farmer_id != farmer.id:
            raise HTTPException(status_code=403, detail="You can only accept offers on your own lots")
        if lot.status not in ("AVAILABLE", "UNDER_OFFER"):
            raise HTTPException(status_code=400, detail=f"This lot is {lot.status} and cannot be sold")

        if offer.quantity_kg > lot.quantity_kg:
            raise HTTPException(status_code=400, detail="Offer quantity exceeds the remaining lot quantity")

        lot.quantity_kg = round(lot.quantity_kg - offer.quantity_kg, 2)
        lot.status = "SOLD" if lot.quantity_kg <= 0 else "AVAILABLE"
        others = []
        if lot.status == "SOLD":
            others = (
                db.query(models.BuyerOffer)
                .filter(models.BuyerOffer.lot_id == lot.id, models.BuyerOffer.id != offer.id,
                        models.BuyerOffer.status == "pending")
                .all()
            )
        market_used = lot.location
        lot_id = lot.id

        # Close out the buyer demand this offer was fulfilling, if any.
        if offer.buyer_demand_id:
            demand = db.query(models.BuyerDemand).filter(
                models.BuyerDemand.id == offer.buyer_demand_id
            ).first()
            if demand and demand.status not in ("FULFILLED", "CANCELLED", "EXPIRED"):
                demand.status = "FULFILLED"

    offer.status = "accepted"
    # reject other pending offers on the same lot/listing
    for o in others:
        o.status = "rejected"
        losing = neg.open_round(db, o)
        if losing:
            neg.close_round(losing, "REJECTED", "system")

    transaction = models.Transaction(
        listing_id=offer.listing_id,
        lot_id=lot_id,
        offer_id=offer.id,
        farmer_id=farmer.id,
        buyer_id=offer.buyer_id,
        final_price_per_kg=offer.offered_price_per_kg,
        quantity_kg=offer.quantity_kg,
        total_amount=round(offer.offered_price_per_kg * offer.quantity_kg, 2),
        market_used=market_used,
        status="OFFER_ACCEPTED",
    )
    db.add(transaction)
    db.flush()  # get transaction.id before commit

    # Seed the event timeline (Phase 12)
    db.add(models.TransactionEvent(
        transaction_id=transaction.id,
        event_type="OFFER_CREATED",
        description="Offer created by buyer",
        performed_by="buyer",
        performed_by_id=offer.buyer_id,
    ))
    db.add(models.TransactionEvent(
        transaction_id=transaction.id,
        event_type="OFFER_ACCEPTED",
        description=f"Offer accepted by {accepted_by}. Transaction initiated.",
        performed_by=accepted_by,
        performed_by_id=farmer.id if accepted_by == "farmer" else offer.buyer_id,
    ))
    neg.record_agreement(db, offer, transaction, accepted_by)
    neg.notify(db, neg.other_party(accepted_by), farmer.id, offer.buyer_id,
               "Offer accepted", f"Terms agreed: ₹{offer.offered_price_per_kg}/kg × {offer.quantity_kg} kg. "
               f"Transaction #{transaction.id} created.", "success")
    db.commit()
    return {"accepted": True, "transaction_id": transaction.id}


@router.patch("/{offer_id}/reject")
def reject_offer(offer_id: int, farmer: models.Farmer = Depends(require_farmer),
                  db: Session = Depends(get_db)):
    offer = db.query(models.BuyerOffer).filter(models.BuyerOffer.id == offer_id).first()
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    if offer.status != "pending":
        raise HTTPException(status_code=400, detail=f"This offer is already {offer.status} and cannot be changed")

    if offer.listing_id:
        listing = db.query(models.CropListing).filter(models.CropListing.id == offer.listing_id).first()
        if not listing or listing.farmer_id != farmer.id:
            raise HTTPException(status_code=403, detail="You can only reject offers on your own listings")
    else:
        lot = db.query(models.Lot).filter(models.Lot.id == offer.lot_id).first()
        if not lot or lot.farmer_id != farmer.id:
            raise HTTPException(status_code=403, detail="You can only reject offers on your own lots")

    reject_offer_core(db, offer, "farmer")
    neg.notify(db, "buyer", farmer.id, offer.buyer_id, "Offer rejected",
               f"The farmer rejected the proposal of ₹{offer.offered_price_per_kg}/kg for {offer.quantity_kg} kg.",
               "warning")
    db.commit()
    return {"rejected": True}


def reject_offer_core(db: Session, offer: models.BuyerOffer, role: str):
    """Reject the open proposal (by the party it was proposed TO)."""
    neg.require_turn(neg.require_open_round(db, offer), role)
    close_offer(db, offer, "rejected", role)


def close_offer(db: Session, offer: models.BuyerOffer, new_status: str, role: str):
    """End a negotiation without a deal ('rejected' or 'withdrawn'): update the
    offer, close its open round, and free the lot if nothing else is pending."""
    neg.ensure_rounds(db, offer)
    if offer.lot_id:
        lot = db.query(models.Lot).filter(models.Lot.id == offer.lot_id).first()
        remaining = (
            db.query(models.BuyerOffer)
            .filter(models.BuyerOffer.lot_id == offer.lot_id, models.BuyerOffer.id != offer.id,
                    models.BuyerOffer.status == "pending")
            .count()
        )
        if lot and remaining == 0 and lot.status == "UNDER_OFFER":
            lot.status = "AVAILABLE"
    offer.status = new_status
    open_round = neg.open_round(db, offer)
    if open_round:
        neg.close_round(open_round, "REJECTED" if new_status == "rejected" else "WITHDRAWN", role)
