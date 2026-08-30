"""
Buyer Verification — Phase 2.

Three trust tiers clearly displayed:
  PLATFORM_VERIFIED  — admin reviewed documents
  DOCUMENT_VERIFIED  — documents submitted, not yet reviewed
  SELF_DECLARED      — buyer filled in their own details
  PENDING            — nothing submitted yet

We never claim government verification.
"""
import datetime as dt
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.auth_utils import require_buyer, require_admin, get_current_user

router = APIRouter(prefix="/buyer-verification", tags=["buyer-verification"])

VALID_STATUSES = {"PENDING", "UNDER_REVIEW", "VERIFIED", "REJECTED", "SUSPENDED"}


# ---------------------------------------------------------------------------
# Buyer — submit / view own verification
# ---------------------------------------------------------------------------

@router.post("", response_model=schemas.BuyerVerificationOut)
def submit_verification(
    payload: schemas.BuyerVerificationCreate,
    buyer: models.Buyer = Depends(require_buyer),
    db: Session = Depends(get_db),
):
    existing = (
        db.query(models.BuyerVerification)
        .filter(models.BuyerVerification.buyer_id == buyer.id)
        .first()
    )
    if existing:
        # Update existing submission
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(existing, field, value)
        # Re-opening a rejected/pending submission bumps it to UNDER_REVIEW
        if existing.verification_status in ("PENDING", "REJECTED"):
            existing.verification_status = "UNDER_REVIEW"
            existing.verification_method = (
                "DOCUMENT_VERIFIED" if payload.document_urls else "SELF_DECLARED"
            )
        db.commit()
        db.refresh(existing)
        return existing

    method = "DOCUMENT_VERIFIED" if payload.document_urls else "SELF_DECLARED"
    verification = models.BuyerVerification(
        buyer_id=buyer.id,
        business_name=payload.business_name,
        business_registration_number=payload.business_registration_number,
        gst_number=payload.gst_number,
        license_number=payload.license_number,
        document_urls=payload.document_urls,
        verification_status="UNDER_REVIEW",
        verification_method=method,
    )
    db.add(verification)
    db.commit()
    db.refresh(verification)
    return verification


@router.get("/me", response_model=schemas.BuyerVerificationOut)
def my_verification(
    buyer: models.Buyer = Depends(require_buyer),
    db: Session = Depends(get_db),
):
    v = db.query(models.BuyerVerification).filter(models.BuyerVerification.buyer_id == buyer.id).first()
    if not v:
        raise HTTPException(status_code=404, detail="No verification submission found. Submit one first.")
    return v


@router.get("/{buyer_id}", response_model=schemas.BuyerVerificationOut)
def get_buyer_verification(
    buyer_id: int,
    db: Session = Depends(get_db),
):
    """Public endpoint — anyone can see a buyer's verification status (not the documents)."""
    v = db.query(models.BuyerVerification).filter(models.BuyerVerification.buyer_id == buyer_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="No verification record for this buyer")
    return v


# ---------------------------------------------------------------------------
# Admin — review and decide
# ---------------------------------------------------------------------------

@router.get("", response_model=List[schemas.BuyerVerificationOut])
def list_verifications(
    status: str = "UNDER_REVIEW",
    admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin only: list pending/under-review verifications."""
    q = db.query(models.BuyerVerification)
    if status:
        q = q.filter(models.BuyerVerification.verification_status == status)
    return q.order_by(models.BuyerVerification.created_at.asc()).all()


@router.patch("/{buyer_id}/approve")
def approve_verification(
    buyer_id: int,
    notes: str = "",
    admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    v = db.query(models.BuyerVerification).filter(models.BuyerVerification.buyer_id == buyer_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="No verification record for this buyer")

    v.verification_status = "VERIFIED"
    v.verification_method = "PLATFORM_VERIFIED"
    v.verification_notes = notes
    v.verified_at = dt.datetime.utcnow()
    v.rejected_reason = None

    # Mirror onto the Buyer row so the match engine sees it without a join
    buyer = db.query(models.Buyer).filter(models.Buyer.id == buyer_id).first()
    if buyer:
        buyer.verification_status = "verified"

    db.commit()
    return {"approved": True, "buyer_id": buyer_id}


@router.patch("/{buyer_id}/reject")
def reject_verification(
    buyer_id: int,
    reason: str = "Documents could not be verified",
    admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    v = db.query(models.BuyerVerification).filter(models.BuyerVerification.buyer_id == buyer_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="No verification record for this buyer")

    v.verification_status = "REJECTED"
    v.rejected_reason = reason

    buyer = db.query(models.Buyer).filter(models.Buyer.id == buyer_id).first()
    if buyer:
        buyer.verification_status = "pending"

    db.commit()
    return {"rejected": True, "buyer_id": buyer_id, "reason": reason}


@router.patch("/{buyer_id}/suspend")
def suspend_buyer(
    buyer_id: int,
    reason: str = "Suspended by admin",
    admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    v = db.query(models.BuyerVerification).filter(models.BuyerVerification.buyer_id == buyer_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="No verification record for this buyer")
    v.verification_status = "SUSPENDED"
    v.verification_notes = reason

    # Mirror onto the Buyer row, same as approve/reject -- without this, a
    # previously-verified buyer stays "verified" on the Buyer row (which is
    # the field the match engine and buyer-facing badges actually read),
    # so a suspended buyer would keep getting the verification bonus in
    # matching and keep showing a verified badge to farmers.
    buyer = db.query(models.Buyer).filter(models.Buyer.id == buyer_id).first()
    if buyer:
        buyer.verification_status = "pending"

    db.commit()
    return {"suspended": True, "buyer_id": buyer_id}
