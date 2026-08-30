from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models
from app.auth_utils import require_farmer
from app.routers.market import _latest_price_row
from app.mock_data.locations import MARKET_BY_NAME
from app.services.buyer_matcher import score_buyers_for_listing, score_buyers_for_lot

router = APIRouter(prefix="/matching", tags=["matching"])


def _build_demands_lookup(db: Session, crop: str) -> dict:
    """Build {buyer_id: [BuyerDemand, ...]} for all ACTIVE demands for a crop."""
    demands = (
        db.query(models.BuyerDemand)
        .filter(models.BuyerDemand.crop == crop, models.BuyerDemand.status == "ACTIVE")
        .all()
    )
    lookup = defaultdict(list)
    for d in demands:
        lookup[d.buyer_id].append(d)
    return dict(lookup)


def _modal_price(db: Session, crop: str, location: str, fallback: float) -> float:
    market_name = location if location in MARKET_BY_NAME else "Bilaspur"
    latest = _latest_price_row(db, crop, market_name)
    return round(latest.modal_price / 100.0, 2) if latest else fallback


@router.get("/listing/{listing_id}")
def match_buyers(listing_id: int, top_n: int = 5, db: Session = Depends(get_db),
                  farmer: models.Farmer = Depends(require_farmer)):
    listing = db.query(models.CropListing).filter(models.CropListing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing.farmer_id != farmer.id:
        raise HTTPException(status_code=403, detail="You can only view buyer matches for your own listings")

    modal_price_per_kg = _modal_price(db, listing.crop, listing.location, listing.expected_price_per_kg)
    demands_lookup = _build_demands_lookup(db, listing.crop)
    buyers = db.query(models.Buyer).all()
    matches = score_buyers_for_listing(listing, buyers, modal_price_per_kg, demands_lookup)

    return {
        "listing_id": listing_id, "crop": listing.crop, "quantity_kg": listing.quantity_kg,
        "market_reference_price_per_kg": modal_price_per_kg,
        "matches": matches[:top_n],
    }


@router.get("/lot/{lot_id}")
def match_buyers_for_lot(lot_id: int, top_n: int = 5, db: Session = Depends(get_db),
                          farmer: models.Farmer = Depends(require_farmer)):
    """Phase 5: match buyers against a Lot (not just a CropListing)."""
    lot = db.query(models.Lot).filter(models.Lot.id == lot_id).first()
    if not lot:
        raise HTTPException(status_code=404, detail="Lot not found")
    if lot.farmer_id != farmer.id:
        raise HTTPException(status_code=403, detail="You can only view buyer matches for your own lots")

    modal_price_per_kg = _modal_price(db, lot.crop, lot.location, lot.expected_price)
    demands_lookup = _build_demands_lookup(db, lot.crop)
    buyers = db.query(models.Buyer).all()
    matches = score_buyers_for_lot(lot, buyers, modal_price_per_kg, demands_lookup)

    return {
        "lot_id": lot_id,
        "lot_number": lot.lot_number,
        "crop": lot.crop,
        "quantity_kg": lot.quantity_kg,
        "grade": lot.grade,
        "quality_score": lot.quality_score,
        "market_reference_price_per_kg": modal_price_per_kg,
        "matches": matches[:top_n],
    }
