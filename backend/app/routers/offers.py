from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.auth_utils import require_buyer, require_farmer

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

    if offer.listing_id:
        listing = db.query(models.CropListing).filter(models.CropListing.id == offer.listing_id).first()
        if not listing or listing.farmer_id != farmer.id:
            raise HTTPException(status_code=403, detail="You can only accept offers on your own listings")
        if listing.status != "active":
            raise HTTPException(status_code=400, detail="This listing is no longer active")

        listing.status = "sold"
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

        lot.status = "SOLD"
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
        if o.lot_id:
            pass  # lot already reassigned to SOLD; nothing further to revert

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
        description=f"Offer of ₹{offer.offered_price_per_kg}/kg created by buyer",
        performed_by="buyer",
        performed_by_id=offer.buyer_id,
    ))
    db.add(models.TransactionEvent(
        transaction_id=transaction.id,
        event_type="OFFER_ACCEPTED",
        description=f"Offer accepted by farmer. Transaction initiated.",
        performed_by="farmer",
        performed_by_id=farmer.id,
    ))
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
        # If no other pending offers remain on this lot, free it back up.
        remaining = (
            db.query(models.BuyerOffer)
            .filter(models.BuyerOffer.lot_id == lot.id, models.BuyerOffer.id != offer.id,
                    models.BuyerOffer.status == "pending")
            .count()
        )
        if remaining == 0 and lot.status == "UNDER_OFFER":
            lot.status = "AVAILABLE"

    offer.status = "rejected"
    db.commit()
    return {"rejected": True}
