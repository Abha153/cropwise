"""
Partner reputation / QoS -- buyers and transport agencies.

Read endpoints return evidence-derived profiles (see services/reputation.py
for the rules). Write endpoints only *record facts* (an outcome, a final
charge, a delivery promise) or handle a partner's right of reply (disputes).
Nothing here ever writes a score.
"""
import datetime as dt
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app import models
from app.auth_utils import get_current_user, require_admin, require_farmer
from app.database import get_db
from app.routers.transactions import _add_event
from app.services import reputation as rep

router = APIRouter(prefix="/reputation", tags=["reputation"])

DISPUTE_TARGETS = {"PERFORMANCE_RECORD", "TRANSPORT_REQUEST"}
ADMIN_DISPUTE_STATUSES = {"UNDER_REVIEW", "UPHELD", "REJECTED"}
PRE_PICKUP = ("REQUESTED", "MATCHED", "CONFIRMED")


# ── schemas ──────────────────────────────────────────────────────────────────
class PerformanceRecordIn(BaseModel):
    transaction_id: int
    metric: str
    result: str
    note: Optional[str] = Field(default=None, max_length=1000)


class FinalChargeIn(BaseModel):
    final_charge: float = Field(gt=0)


class DeliveryPromiseIn(BaseModel):
    promised_delivery_by: str       # ISO date, YYYY-MM-DD


class DisputeIn(BaseModel):
    target_type: str
    target_id: int
    reason: str = Field(min_length=10, max_length=2000)
    evidence_urls: List[str] = []


class DisputeDecisionIn(BaseModel):
    status: str
    admin_note: Optional[str] = Field(default=None, max_length=2000)


def _dispute_dict(d: models.ReputationDispute) -> dict:
    return {
        "id": d.id, "subject_role": d.subject_role, "subject_id": d.subject_id,
        "target_type": d.target_type, "target_id": d.target_id, "reason": d.reason,
        "evidence_urls": d.evidence_urls or [], "status": d.status, "admin_note": d.admin_note,
        "created_at": d.created_at.isoformat() if d.created_at else None,
        "resolved_at": d.resolved_at.isoformat() if d.resolved_at else None,
    }


# ── read: methodology + profiles ─────────────────────────────────────────────
@router.get("/methodology")
def get_methodology():
    return rep.methodology()


@router.get("/transporters")
def list_transporter_profiles(current=Depends(get_current_user), db: Session = Depends(get_db)):
    now = dt.datetime.utcnow()
    ids = [t.id for t in db.query(models.Transporter.id).all()]
    profiles = [p for p in (rep.transporter_profile(db, i, now) for i in ids) if p]
    return rep.rank_profiles(profiles)


@router.get("/transporters/{transporter_id}")
def get_transporter_profile(transporter_id: int, current=Depends(get_current_user),
                            db: Session = Depends(get_db)):
    p = rep.transporter_profile(db, transporter_id)
    if not p:
        raise HTTPException(status_code=404, detail="Transport agency not found")
    return p


@router.get("/buyers")
def list_buyer_profiles(current=Depends(get_current_user), db: Session = Depends(get_db)):
    now = dt.datetime.utcnow()
    ids = [b.id for b in db.query(models.Buyer.id).all()]
    profiles = [p for p in (rep.buyer_profile(db, i, now) for i in ids) if p]
    return rep.rank_profiles(profiles)


@router.get("/buyers/{buyer_id}")
def get_buyer_profile(buyer_id: int, current=Depends(get_current_user), db: Session = Depends(get_db)):
    p = rep.buyer_profile(db, buyer_id)
    if not p:
        raise HTTPException(status_code=404, detail="Buyer not found")
    return p


# ── read: the evidence behind MY profile (so I can see and contest it) ───────
@router.get("/me/evidence")
def my_evidence(current=Depends(get_current_user), db: Session = Depends(get_db)):
    role, user = current["role"], current["user"]
    if role == "transporter":
        reqs = (db.query(models.TransportRequest)
                .filter(models.TransportRequest.transporter_id == user.id)
                .order_by(models.TransportRequest.id.desc()).all())
        return {"role": role, "items": [{
            "target_type": "TRANSPORT_REQUEST", "target_id": r.id, "status": r.status,
            "scheduled_pickup": r.pickup_date, "picked_up_at": r.picked_up_at.isoformat() if r.picked_up_at else None,
            "agreed_price": r.transporter_agreed_price if r.transporter_agreed_price is not None else r.agreed_price,
            "final_charge": r.final_charge, "cancelled_by": r.cancelled_by,
            "promised_delivery_by": r.promised_delivery_by,
            "delivered_at": r.delivered_at.isoformat() if r.delivered_at else None,
        } for r in reqs]}
    if role == "buyer":
        recs = (db.query(models.PerformanceRecord)
                .filter(models.PerformanceRecord.subject_role == "buyer",
                        models.PerformanceRecord.subject_id == user.id)
                .order_by(models.PerformanceRecord.id.desc()).all())
        return {"role": role, "items": [{
            "target_type": "PERFORMANCE_RECORD", "target_id": r.id, "transaction_id": r.transaction_id,
            "metric": r.metric, "result": r.result, "note": r.note,
            "recorded_at": r.created_at.isoformat() if r.created_at else None,
        } for r in recs]}
    raise HTTPException(status_code=403, detail="Only buyers and transport agencies have a reputation profile")


# ── write: record facts (farmer side) ────────────────────────────────────────
@router.post("/records", status_code=201)
def record_buyer_outcome(payload: PerformanceRecordIn, farmer=Depends(require_farmer),
                         db: Session = Depends(get_db)):
    metric, result = payload.metric.upper(), payload.result.upper()
    if metric not in rep.BUYER_METRICS:
        raise HTTPException(status_code=400, detail=f"metric must be one of {sorted(rep.BUYER_METRICS)}")
    if result not in rep.BUYER_METRICS[metric]:
        raise HTTPException(status_code=400, detail=f"result for {metric} must be one of {sorted(rep.BUYER_METRICS[metric])}")
    txn = db.query(models.Transaction).filter(models.Transaction.id == payload.transaction_id).first()
    if not txn or txn.farmer_id != farmer.id:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if db.query(models.PerformanceRecord).filter(
            models.PerformanceRecord.transaction_id == txn.id,
            models.PerformanceRecord.metric == metric).first():
        raise HTTPException(status_code=409, detail="This outcome is already recorded for the transaction")
    rec = models.PerformanceRecord(
        subject_role="buyer", subject_id=txn.buyer_id, transaction_id=txn.id,
        metric=metric, result=result, note=payload.note,
        recorded_by_role="farmer", recorded_by_id=farmer.id)
    db.add(rec)
    _add_event(db, txn.id, "PERFORMANCE_RECORDED",
               f"Farmer recorded {metric} = {result}", "farmer", farmer.id)
    db.commit()
    db.refresh(rec)
    return {"id": rec.id, "metric": rec.metric, "result": rec.result, "transaction_id": rec.transaction_id}


@router.post("/transport/{request_id}/final-charge")
def record_final_charge(request_id: int, payload: FinalChargeIn, farmer=Depends(require_farmer),
                        db: Session = Depends(get_db)):
    r = db.query(models.TransportRequest).filter(models.TransportRequest.id == request_id).first()
    if not r or r.farmer_id != farmer.id:
        raise HTTPException(status_code=404, detail="Transport request not found")
    if r.status not in rep.COMPLETED_TRANSPORT:
        raise HTTPException(status_code=400, detail="Final charge can be recorded only after delivery")
    if r.final_charge is not None:
        raise HTTPException(status_code=409, detail="Final charge is already recorded; the agency can contest it")
    r.final_charge = payload.final_charge
    r.final_charge_recorded_at = dt.datetime.utcnow()
    db.commit()
    return {"request_id": r.id, "final_charge": r.final_charge}


@router.post("/transport/{request_id}/delivery-promise")
def record_delivery_promise(request_id: int, payload: DeliveryPromiseIn, current=Depends(get_current_user),
                            db: Session = Depends(get_db)):
    role, user = current["role"], current["user"]
    r = db.query(models.TransportRequest).filter(models.TransportRequest.id == request_id).first()
    is_party = r and ((role == "farmer" and r.farmer_id == user.id)
                      or (role == "transporter" and r.transporter_id == user.id))
    if not is_party:
        raise HTTPException(status_code=404, detail="Transport request not found")
    try:
        dt.date.fromisoformat(payload.promised_delivery_by)
    except ValueError:
        raise HTTPException(status_code=400, detail="promised_delivery_by must be an ISO date (YYYY-MM-DD)")
    if r.status not in PRE_PICKUP:
        raise HTTPException(status_code=400, detail="A delivery promise can be set only before pickup")
    if r.promised_delivery_by:
        raise HTTPException(status_code=409, detail="A delivery promise is already recorded")
    r.promised_delivery_by = payload.promised_delivery_by
    db.commit()
    return {"request_id": r.id, "promised_delivery_by": r.promised_delivery_by, "recorded_by": role}


# ── right of reply: disputes ─────────────────────────────────────────────────
@router.post("/disputes", status_code=201)
def raise_dispute(payload: DisputeIn, current=Depends(get_current_user), db: Session = Depends(get_db)):
    role, user = current["role"], current["user"]
    if role not in ("buyer", "transporter"):
        raise HTTPException(status_code=403, detail="Only the rated partner can contest its own evidence")
    target = payload.target_type.upper()
    if target not in DISPUTE_TARGETS:
        raise HTTPException(status_code=400, detail=f"target_type must be one of {sorted(DISPUTE_TARGETS)}")
    if target == "PERFORMANCE_RECORD":
        row = db.query(models.PerformanceRecord).filter(models.PerformanceRecord.id == payload.target_id).first()
        owned = row and role == "buyer" and row.subject_role == "buyer" and row.subject_id == user.id
    else:
        row = db.query(models.TransportRequest).filter(models.TransportRequest.id == payload.target_id).first()
        owned = row and role == "transporter" and row.transporter_id == user.id
    if not owned:
        raise HTTPException(status_code=404, detail="Evidence item not found")
    if db.query(models.ReputationDispute).filter(
            models.ReputationDispute.target_type == target,
            models.ReputationDispute.target_id == payload.target_id,
            models.ReputationDispute.subject_role == role,
            models.ReputationDispute.subject_id == user.id).first():
        raise HTTPException(status_code=409, detail="You have already contested this item")
    d = models.ReputationDispute(
        subject_role=role, subject_id=user.id, target_type=target, target_id=payload.target_id,
        reason=payload.reason, evidence_urls=payload.evidence_urls, status="OPEN")
    db.add(d)
    db.commit()
    db.refresh(d)
    return _dispute_dict(d)


@router.get("/disputes/mine")
def my_disputes(current=Depends(get_current_user), db: Session = Depends(get_db)):
    role, user = current["role"], current["user"]
    if role not in ("buyer", "transporter"):
        return []
    rows = (db.query(models.ReputationDispute)
            .filter(models.ReputationDispute.subject_role == role,
                    models.ReputationDispute.subject_id == user.id)
            .order_by(models.ReputationDispute.id.desc()).all())
    return [_dispute_dict(d) for d in rows]


@router.get("/admin/disputes")
def admin_list_disputes(status: Optional[str] = None, admin=Depends(require_admin),
                        db: Session = Depends(get_db)):
    q = db.query(models.ReputationDispute)
    if status:
        q = q.filter(models.ReputationDispute.status == status.upper())
    return [_dispute_dict(d) for d in q.order_by(models.ReputationDispute.id.desc()).limit(100).all()]


@router.patch("/admin/disputes/{dispute_id}")
def admin_decide_dispute(dispute_id: int, payload: DisputeDecisionIn, admin=Depends(require_admin),
                         db: Session = Depends(get_db)):
    d = db.query(models.ReputationDispute).filter(models.ReputationDispute.id == dispute_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Dispute not found")
    new = payload.status.upper()
    if new not in ADMIN_DISPUTE_STATUSES:
        raise HTTPException(status_code=400, detail=f"status must be one of {sorted(ADMIN_DISPUTE_STATUSES)}")
    if d.status in ("UPHELD", "REJECTED"):
        raise HTTPException(status_code=409, detail="This dispute is already decided")
    if new in ("UPHELD", "REJECTED"):
        if not (payload.admin_note or "").strip():
            raise HTTPException(status_code=400, detail="A written reason is required to decide a dispute")
        d.resolved_at = dt.datetime.utcnow()
    d.status = new
    if payload.admin_note:
        d.admin_note = payload.admin_note
    db.commit()
    db.refresh(d)
    return _dispute_dict(d)
