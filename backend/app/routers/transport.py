"""
Phase 9 — Transport / Logistics Coordination
Upgrades FarmPool calculator into a real coordination workflow.
"""
import datetime as dt
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app import models
from app.auth_utils import require_farmer
from app.routers.transactions import _add_event, _normalize_status

router = APIRouter(prefix="/transport", tags=["transport"])

# Status flow
VALID_TRANSITIONS = {
    "REQUESTED": ["MATCHED", "CANCELLED"],
    "MATCHED":   ["CONFIRMED", "CANCELLED"],
    "CONFIRMED": ["PICKED_UP", "CANCELLED"],
    "PICKED_UP": ["IN_TRANSIT"],
    "IN_TRANSIT": ["DELIVERED"],
    "DELIVERED": [],
    "CANCELLED": [],
}

# Built-in vehicle options (from existing logistics mock data)
VEHICLE_OPTIONS = [
    {"vehicle": "Mahindra Bolero Pickup", "capacity_kg": 1500, "cost_per_km": 14, "type": "mini-truck"},
    {"vehicle": "Tata Ace (Chhota Hathi)", "capacity_kg": 750, "cost_per_km": 9, "type": "mini-truck"},
    {"vehicle": "Eicher 14ft Truck", "capacity_kg": 5000, "cost_per_km": 22, "type": "truck"},
    {"vehicle": "Tata 407 Truck", "capacity_kg": 2500, "cost_per_km": 17, "type": "truck"},
]


# ─── create request ───────────────────────────────────────────────────────────

@router.post("/requests")
def create_transport_request(
    payload: dict,
    farmer: models.Farmer = Depends(require_farmer),
    db: Session = Depends(get_db),
):
    """Farmer creates a transport request for a lot/transaction."""
    required = ["pickup_location", "destination"]
    for f in required:
        if not payload.get(f):
            raise HTTPException(status_code=422, detail=f"{f} is required")

    lot_id = payload.get("lot_id")
    if lot_id:
        lot = db.query(models.Lot).filter(models.Lot.id == lot_id, models.Lot.farmer_id == farmer.id).first()
        if not lot:
            raise HTTPException(status_code=404, detail="Lot not found or not yours")

    # Validate + link the transaction this transport request fulfils, so
    # transport progress can drive the transaction lifecycle instead of the
    # two staying disconnected.
    transaction_id = payload.get("transaction_id")
    txn = None
    if transaction_id:
        txn = db.query(models.Transaction).filter(models.Transaction.id == transaction_id).first()
        if not txn or txn.farmer_id != farmer.id:
            raise HTTPException(status_code=404, detail="Transaction not found or not yours")

    req = models.TransportRequest(
        lot_id=lot_id,
        transaction_id=transaction_id,
        farmer_id=farmer.id,
        buyer_id=payload.get("buyer_id") or (txn.buyer_id if txn else None),
        pickup_location=payload["pickup_location"],
        destination=payload["destination"],
        pickup_date=payload.get("pickup_date"),
        pickup_time=payload.get("pickup_time"),
        vehicle_type=payload.get("vehicle_type"),
        quantity_kg=payload.get("quantity_kg"),
        shared_transport=payload.get("shared_transport", False),
        estimated_cost=payload.get("estimated_cost"),
        status="REQUESTED",
    )
    db.add(req)

    # If the transaction is confirmed and waiting on logistics, move it into
    # LOGISTICS_PENDING now that a transport request actually exists for it.
    if txn and _normalize_status(txn.status) == "ORDER_CONFIRMED":
        txn.status = "LOGISTICS_PENDING"
        txn.updated_at = dt.datetime.utcnow()
        _add_event(db, txn.id, "LOGISTICS_PENDING",
                   "Transport requested by farmer", "farmer", farmer.id)

    db.commit()
    db.refresh(req)

    # Auto-match: if shared transport, scan for compatible requests
    if req.shared_transport:
        _try_match_shared(req, db)

    return _request_dict(req)


def _try_match_shared(req: models.TransportRequest, db: Session):
    """Simple shared-transport matching: find another REQUESTED request going same route."""
    others = (
        db.query(models.TransportRequest)
        .filter(
            models.TransportRequest.id != req.id,
            models.TransportRequest.destination == req.destination,
            models.TransportRequest.status == "REQUESTED",
            models.TransportRequest.shared_transport == True,
        )
        .all()
    )
    if others:
        req.status = "MATCHED"
        db.commit()


# ─── list / get ──────────────────────────────────────────────────────────────

@router.get("/requests/mine")
def my_requests(farmer: models.Farmer = Depends(require_farmer), db: Session = Depends(get_db)):
    reqs = (
        db.query(models.TransportRequest)
        .filter(models.TransportRequest.farmer_id == farmer.id)
        .order_by(models.TransportRequest.created_at.desc())
        .all()
    )
    return [_request_dict(r) for r in reqs]


@router.get("/requests/{request_id}")
def get_request(
    request_id: int,
    farmer: models.Farmer = Depends(require_farmer),
    db: Session = Depends(get_db),
):
    r = db.query(models.TransportRequest).filter(models.TransportRequest.id == request_id).first()
    if not r or r.farmer_id != farmer.id:
        raise HTTPException(status_code=404, detail="Transport request not found")
    return _request_dict(r)


# ─── status update ────────────────────────────────────────────────────────────

@router.patch("/requests/{request_id}/status")
def update_status(
    request_id: int,
    payload: dict,
    farmer: models.Farmer = Depends(require_farmer),
    db: Session = Depends(get_db),
):
    r = db.query(models.TransportRequest).filter(models.TransportRequest.id == request_id).first()
    if not r or r.farmer_id != farmer.id:
        raise HTTPException(status_code=404, detail="Transport request not found")

    new_status = payload.get("status", "").upper()
    if new_status not in VALID_TRANSITIONS.get(r.status, []):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot transition from {r.status} to {new_status}. "
                   f"Valid transitions: {VALID_TRANSITIONS.get(r.status, [])}",
        )
    r.status = new_status
    if payload.get("driver_name"):
        r.driver_name = payload["driver_name"]
    if payload.get("driver_contact"):
        r.driver_contact = payload["driver_contact"]
    if payload.get("vehicle_type"):
        r.vehicle_type = payload["vehicle_type"]

    # If lot exists update its status too
    if r.lot_id and new_status in ("PICKED_UP", "IN_TRANSIT", "DELIVERED"):
        lot = db.query(models.Lot).filter(models.Lot.id == r.lot_id).first()
        if lot:
            if new_status == "PICKED_UP":
                lot.status = "IN_TRANSIT"
            elif new_status == "DELIVERED":
                lot.status = "DELIVERED"

    # Keep the linked transaction's lifecycle status in sync with real
    # transport events, so transport doesn't stay an isolated module.
    # Guarded by the transaction's current status so an out-of-order or
    # duplicate transport update can't skip/rewind transaction states.
    txn = None
    if r.transaction_id:
        txn = db.query(models.Transaction).filter(models.Transaction.id == r.transaction_id).first()
    if txn:
        current = _normalize_status(txn.status)
        transport_to_txn = {
            "CONFIRMED": ("LOGISTICS_PENDING", "LOGISTICS_CONFIRMED", "Transport confirmed"),
            "PICKED_UP": ("LOGISTICS_CONFIRMED", "PICKED_UP", "Produce picked up from farm"),
            "IN_TRANSIT": ("PICKED_UP", "IN_TRANSIT", "In transit to delivery location"),
            "DELIVERED": ("IN_TRANSIT", "DELIVERED", "Delivery confirmed via transport tracking"),
        }
        mapping = transport_to_txn.get(new_status)
        if mapping:
            required_from, txn_new_status, description = mapping
            if current == required_from:
                txn.status = txn_new_status
                txn.updated_at = dt.datetime.utcnow()
                _add_event(db, txn.id, txn_new_status, description, "farmer", r.farmer_id)

    db.commit()
    db.refresh(r)
    return _request_dict(r)


# ─── cancel ──────────────────────────────────────────────────────────────────

@router.patch("/requests/{request_id}/cancel")
def cancel_request(
    request_id: int,
    farmer: models.Farmer = Depends(require_farmer),
    db: Session = Depends(get_db),
):
    r = db.query(models.TransportRequest).filter(models.TransportRequest.id == request_id).first()
    if not r or r.farmer_id != farmer.id:
        raise HTTPException(status_code=404, detail="Transport request not found")
    if r.status in ("DELIVERED", "CANCELLED"):
        raise HTTPException(status_code=400, detail=f"Cannot cancel a request in status {r.status}")
    r.status = "CANCELLED"
    db.commit()
    return {"cancelled": True}


# ─── vehicle options ─────────────────────────────────────────────────────────

@router.get("/vehicle-options")
def vehicle_options(quantity_kg: Optional[float] = Query(None)):
    """Return suitable vehicle options, optionally filtered by capacity."""
    if quantity_kg:
        return [v for v in VEHICLE_OPTIONS if v["capacity_kg"] >= quantity_kg]
    return VEHICLE_OPTIONS


# ─── helper ──────────────────────────────────────────────────────────────────

def _request_dict(r: models.TransportRequest) -> dict:
    return {
        "id": r.id,
        "lot_id": r.lot_id,
        "transaction_id": r.transaction_id,
        "farmer_id": r.farmer_id,
        "buyer_id": r.buyer_id,
        "pickup_location": r.pickup_location,
        "destination": r.destination,
        "pickup_date": r.pickup_date,
        "pickup_time": r.pickup_time,
        "vehicle_type": r.vehicle_type,
        "driver_name": r.driver_name,
        "driver_contact": r.driver_contact,
        "vehicle_capacity": r.vehicle_capacity,
        "quantity_kg": r.quantity_kg,
        "estimated_cost": r.estimated_cost,
        "shared_transport": r.shared_transport,
        "status": r.status,
        "status_label": _status_label(r.status),
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "updated_at": r.updated_at.isoformat() if r.updated_at else None,
    }


def _status_label(status: str) -> str:
    return {
        "REQUESTED": "Transport Requested",
        "MATCHED": "Vehicle Matched",
        "CONFIRMED": "Pickup Confirmed",
        "PICKED_UP": "Goods Picked Up",
        "IN_TRANSIT": "In Transit",
        "DELIVERED": "Delivered",
        "CANCELLED": "Cancelled",
    }.get(status, status)
