"""
Partner reputation / service quality (QoS).

Design rules -- these are the whole point of the module:

* Every figure is computed from rows that already exist in the database.
  Nothing is defaulted, seeded, smoothed or estimated. (The legacy
  ``Buyer.reliability_score`` / ``payment_history_score`` columns are seeded
  defaults, NOT evidence, and are deliberately never read here.)
* Each indicator reports ``numerator`` / ``denominator`` so the farmer can see
  the sample behind it, plus the time of the latest event ("recency").
* An indicator with no usable evidence has ``status = "not_recorded"`` and
  ``value = None`` -- it is never shown as 0 % and never penalises anyone.
* A partner with fewer than ``MIN_COMPLETED_FOR_PROFILE`` completed outcomes is
  labelled "Insufficient history" instead of being scored.
* Evidence that the partner has contested (open / under review / upheld
  dispute) is excluded from their rates and counted separately.
* Ranking uses the Wilson lower confidence bound, so a 5/5 record ranks below
  a 95/100 record. There is no composite 0-100 "score".

The policy constants below are tunable parameters, not measured results.
"""
from __future__ import annotations

import datetime as dt
import math
from typing import Dict, Iterable, List, Optional, Set, Tuple

from sqlalchemy.orm import Session

from app import models

# ── tunable policy parameters ────────────────────────────────────────────────
MIN_COMPLETED_FOR_PROFILE = 3            # below this -> "Insufficient history"
PICKUP_GRACE = dt.timedelta(hours=2)     # pickup within grace of schedule = on time
QUOTE_TOLERANCE_PCT = 5.0                # final charge <= agreed * (1 + 5 %) = accurate
RECENT_WINDOW_DAYS = 90
IST_OFFSET = dt.timedelta(hours=5, minutes=30)   # pickup_date/time are entered in IST

LABEL_INSUFFICIENT = "Insufficient history"
LABEL_ESTABLISHED = "Evidence-based profile"

COMPLETED_TRANSPORT = ("DELIVERED", "COMPLETED")
CONTESTING = ("OPEN", "UNDER_REVIEW", "UPHELD")     # dispute states that exclude evidence

BUYER_METRICS = {
    "BUYER_PICKUP": {"ON_TIME", "LATE", "NO_SHOW"},
    "BUYER_TERMS": {"AS_AGREED", "DEVIATED"},
}
GOOD_RESULTS = {"ON_TIME", "AS_AGREED"}


# ── small pure helpers (unit-tested without a database) ──────────────────────
def wilson_lower_bound(successes: int, total: int, z: float = 1.96) -> Optional[float]:
    """95 % lower confidence bound of a proportion. None when total == 0."""
    if total <= 0:
        return None
    p = successes / total
    denom = 1 + z * z / total
    centre = p + z * z / (2 * total)
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total)
    return round((centre - margin) / denom, 4)


def indicator(key: str, label: str, numerator: int, denominator: int, *,
              last_event_at: Optional[dt.datetime] = None,
              detail: Optional[str] = None,
              excluded_under_review: int = 0,
              unavailable_reason: Optional[str] = None) -> Dict:
    """One reputation indicator. ``value`` is a 0-1 proportion or None."""
    measured = denominator > 0
    return {
        "key": key,
        "label": label,
        "status": "measured" if measured else "not_recorded",
        "value": round(numerator / denominator, 4) if measured else None,
        "numerator": numerator if measured else None,
        "denominator": denominator if measured else 0,
        "last_event_at": last_event_at.isoformat() if (measured and last_event_at) else None,
        "excluded_under_review": excluded_under_review,
        "detail": detail if measured else (unavailable_reason or "No recorded evidence yet"),
    }


def scheduled_pickup_utc(pickup_date: Optional[str], pickup_time: Optional[str]) -> Optional[dt.datetime]:
    """Scheduled pickup as naive UTC. Date/time are entered in IST. With no
    time of day the pickup is due by the END of that date."""
    if not pickup_date:
        return None
    try:
        d = dt.date.fromisoformat(pickup_date.strip()[:10])
    except ValueError:
        return None
    t = None
    if pickup_time:
        for fmt in ("%H:%M", "%H:%M:%S", "%I:%M %p", "%I:%M%p"):
            try:
                t = dt.datetime.strptime(pickup_time.strip().upper(), fmt).time()
                break
            except ValueError:
                continue
    local = dt.datetime.combine(d, t) if t else dt.datetime.combine(d, dt.time(23, 59, 59))
    return local - IST_OFFSET


def pickup_on_time(scheduled_utc: Optional[dt.datetime], actual_utc: Optional[dt.datetime]) -> Optional[bool]:
    if scheduled_utc is None or actual_utc is None:
        return None
    return actual_utc <= scheduled_utc + PICKUP_GRACE


def quote_deviation_pct(agreed: Optional[float], final: Optional[float]) -> Optional[float]:
    if agreed is None or final is None or agreed <= 0:
        return None
    return round((final - agreed) / agreed * 100.0, 2)


def quote_accurate(dev_pct: Optional[float]) -> Optional[bool]:
    """Only overcharging counts against accuracy; charging less is fine."""
    if dev_pct is None:
        return None
    return dev_pct <= QUOTE_TOLERANCE_PCT


def _latest(values: Iterable[Optional[dt.datetime]]) -> Optional[dt.datetime]:
    vals = [v for v in values if v]
    return max(vals) if vals else None


def _normalize_txn_status(raw: Optional[str]) -> str:
    return "COMPLETED" if raw and raw.lower() == "completed" else (raw or "")


# ── evidence-exclusion lookup ────────────────────────────────────────────────
def _contested(db: Session, subject_role: str, subject_id: int) -> Dict[Tuple[str, int], str]:
    rows = (db.query(models.ReputationDispute)
            .filter(models.ReputationDispute.subject_role == subject_role,
                    models.ReputationDispute.subject_id == subject_id,
                    models.ReputationDispute.status.in_(CONTESTING)).all())
    return {(r.target_type, r.target_id): r.status for r in rows}


def _complaint_summary(db: Session, subject_role: str, subject_id: int) -> Dict:
    """Complaints are shown as counts by status. They are NOT turned into a
    penalty rate: an OPEN complaint is an allegation, not a finding, and the
    Grievance table records no 'upheld' outcome."""
    rows = (db.query(models.Grievance)
            .filter(models.Grievance.against_user == subject_role,
                    models.Grievance.against_user_id == subject_id).all())
    pending = [g for g in rows if g.status in ("OPEN", "UNDER_REVIEW", "WAITING_FOR_EVIDENCE")]
    resolved = [g for g in rows if g.status in ("RESOLVED", "CLOSED")]
    dismissed = [g for g in rows if g.status == "REJECTED"]
    return {
        "recorded": len(rows),
        "pending_review": len(pending),
        "resolved": len(resolved),
        "dismissed": len(dismissed),
        "last_event_at": (_latest(g.created_at for g in rows).isoformat() if rows else None),
        "note": "Complaints are allegations until reviewed; pending ones are shown but not counted against the partner.",
    }


def _recency(events: List[Optional[dt.datetime]], now: dt.datetime) -> Dict:
    last = _latest(events)
    cutoff = now - dt.timedelta(days=RECENT_WINDOW_DAYS)
    return {
        "last_activity_at": last.isoformat() if last else None,
        "events_last_%d_days" % RECENT_WINDOW_DAYS: sum(1 for e in events if e and e >= cutoff),
    }


def _label(completed: int) -> Dict:
    ok = completed >= MIN_COMPLETED_FOR_PROFILE
    return {
        "label": LABEL_ESTABLISHED if ok else LABEL_INSUFFICIENT,
        "sufficient_history": ok,
        "completed_outcomes": completed,
        "minimum_required": MIN_COMPLETED_FOR_PROFILE,
    }


# ── transport agency profile ─────────────────────────────────────────────────
def transporter_profile(db: Session, transporter_id: int, now: Optional[dt.datetime] = None) -> Optional[Dict]:
    now = now or dt.datetime.utcnow()
    t = db.query(models.Transporter).filter(models.Transporter.id == transporter_id).first()
    if not t:
        return None
    contested = _contested(db, "transporter", transporter_id)
    reqs = (db.query(models.TransportRequest)
            .filter(models.TransportRequest.transporter_id == transporter_id).all())

    def under_review(r):  # contested wholesale -> excluded from every transport rate
        return ("TRANSPORT_REQUEST", r.id) in contested

    live = [r for r in reqs if not under_review(r)]
    n_excluded = len(reqs) - len(live)

    completed = [r for r in live if r.status in COMPLETED_TRANSPORT]
    cancelled_by_agency = [r for r in live if r.status == "CANCELLED" and r.cancelled_by == "transporter"]
    cancelled_other = [r for r in live if r.status == "CANCELLED" and r.cancelled_by != "transporter"]

    # on-time pickup
    pu_ok = pu_n = 0
    pu_last = []
    for r in live:
        verdict = pickup_on_time(scheduled_pickup_utc(r.pickup_date, r.pickup_time), r.picked_up_at)
        if verdict is None:
            continue
        pu_n += 1
        pu_ok += 1 if verdict else 0
        pu_last.append(r.picked_up_at)

    # on-time delivery (only where a delivery promise was recorded)
    dl_ok = dl_n = 0
    dl_last = []
    for r in completed:
        if not (r.promised_delivery_by and r.delivered_at):
            continue
        try:
            deadline = dt.datetime.combine(dt.date.fromisoformat(r.promised_delivery_by[:10]),
                                           dt.time(23, 59, 59)) - IST_OFFSET
        except ValueError:
            continue
        dl_n += 1
        dl_ok += 1 if r.delivered_at <= deadline else 0
        dl_last.append(r.delivered_at)

    # quote accuracy: agreed price vs the charge actually billed
    qa_ok = qa_n = 0
    devs: List[float] = []
    qa_last = []
    for r in live:
        agreed = r.transporter_agreed_price if r.transporter_agreed_price is not None else r.agreed_price
        dev = quote_deviation_pct(agreed, r.final_charge)
        if dev is None:
            continue
        qa_n += 1
        qa_ok += 1 if quote_accurate(dev) else 0
        devs.append(dev)
        qa_last.append(r.final_charge_recorded_at)
    qa_detail = (f"Average deviation from agreed price {round(sum(devs) / len(devs), 2)} % "
                 f"(accurate = billed within +{QUOTE_TOLERANCE_PCT:g} % of agreed)") if devs else None

    # fulfilment: trips that were completed vs cancelled BY the agency
    f_den = len(completed) + len(cancelled_by_agency)

    indicators = [
        indicator("on_time_pickup", "On-time pickup", pu_ok, pu_n, last_event_at=_latest(pu_last),
                  detail=f"Picked up within {int(PICKUP_GRACE.total_seconds() // 3600)} h of the scheduled time",
                  unavailable_reason="No trip has both a scheduled and a recorded pickup time"),
        indicator("on_time_delivery", "On-time delivery", dl_ok, dl_n, last_event_at=_latest(dl_last),
                  detail="Delivered by the promised delivery date",
                  unavailable_reason="No trip has a recorded delivery promise"),
        indicator("quote_accuracy", "Quote accuracy", qa_ok, qa_n, last_event_at=_latest(qa_last),
                  detail=qa_detail,
                  unavailable_reason="No trip has both an agreed price and a recorded final charge"),
        indicator("trip_fulfilment", "Completed vs agency-cancelled trips", len(completed), f_den,
                  last_event_at=_latest([r.completed_at or r.delivered_at for r in completed]
                                        + [r.cancelled_at for r in cancelled_by_agency]),
                  detail=f"{len(completed)} completed, {len(cancelled_by_agency)} cancelled by the agency"),
    ]

    review_rows = (db.query(models.TransportReview)
                   .filter(models.TransportReview.reviewee_role == "transporter",
                           models.TransportReview.reviewee_id == transporter_id).all())
    events = ([r.delivered_at or r.completed_at for r in completed]
              + [r.cancelled_at for r in cancelled_by_agency])

    return {
        "partner_type": "transporter",
        "partner_id": transporter_id,
        "name": t.business_name or t.name,
        **_label(len(completed)),
        "trip_history": {
            "completed": len(completed),
            "cancelled_by_agency": len(cancelled_by_agency),
            "cancelled_other_or_unrecorded": len(cancelled_other),
            "contested_items_under_review": n_excluded,
        },
        "indicators": indicators,
        "complaints_and_disputes": _complaint_summary(db, "transporter", transporter_id),
        "recency": _recency(events, now),
        "farmer_feedback": {
            "count": len(review_rows),
            "average_overall": (round(sum(r.rating for r in review_rows) / len(review_rows), 2)
                                if review_rows else None),
            "note": "Opinion-based feedback, shown separately and not used in ranking.",
        },
        "ranking": _ranking(len(completed) >= MIN_COMPLETED_FOR_PROFILE,
                            [(pu_ok, pu_n), (qa_ok, qa_n), (len(completed), f_den)]),
    }


# ── buyer profile ────────────────────────────────────────────────────────────
def buyer_profile(db: Session, buyer_id: int, now: Optional[dt.datetime] = None) -> Optional[Dict]:
    now = now or dt.datetime.utcnow()
    b = db.query(models.Buyer).filter(models.Buyer.id == buyer_id).first()
    if not b:
        return None
    contested = _contested(db, "buyer", buyer_id)
    txns = db.query(models.Transaction).filter(models.Transaction.buyer_id == buyer_id).all()
    status_of = {t.id: _normalize_txn_status(t.status) for t in txns}
    completed = [t for t in txns if status_of[t.id] == "COMPLETED"]
    cancelled = [t for t in txns if status_of[t.id] == "CANCELLED"]
    in_progress = len(txns) - len(completed) - len(cancelled)

    recs = (db.query(models.PerformanceRecord)
            .filter(models.PerformanceRecord.subject_role == "buyer",
                    models.PerformanceRecord.subject_id == buyer_id).all())

    def metric_indicator(key, label, metric, detail):
        rows = [r for r in recs if r.metric == metric]
        live = [r for r in rows if ("PERFORMANCE_RECORD", r.id) not in contested]
        ok = sum(1 for r in live if r.result in GOOD_RESULTS)
        ind = indicator(key, label, ok, len(live), last_event_at=_latest(r.created_at for r in live),
                        detail=detail, excluded_under_review=len(rows) - len(live),
                        unavailable_reason="No outcome recorded by a farmer yet")
        return ind, ok, len(live)

    pickup_ind, pk_ok, pk_n = metric_indicator(
        "pickup_reliability", "Pickup reliability", "BUYER_PICKUP",
        "Pickups recorded by farmers as on time (vs late / no-show)")
    terms_ind, tm_ok, tm_n = metric_indicator(
        "terms_adherence", "Adherence to agreed terms", "BUYER_TERMS",
        "Transactions recorded by farmers as fulfilled on the agreed price/quantity/quality")

    # payment status: simulated payments are not evidence
    pays = db.query(models.Payment).filter(models.Payment.buyer_id == buyer_id).all()
    real = [p for p in pays if not p.is_demo]
    demo_n = len(pays) - len(real)
    settled = [p for p in real if p.payment_status in ("PAID", "FAILED", "DISPUTED")
               or (p.payment_status in ("PENDING", "DUE", "INITIATED") and _overdue(p, now))]
    paid_on_time = [p for p in settled if p.payment_status == "PAID" and not _paid_late(p)]
    pay_ind = indicator(
        "payment_status", "Payment status", len(paid_on_time), len(settled),
        last_event_at=_latest(p.received_at or p.updated_at for p in settled),
        detail="Real payments received on or before the due date (due date required)",
        unavailable_reason=("Payments in this deployment are simulated and excluded from reputation"
                            if demo_n and not real else "No settled, non-simulated payments recorded"))
    pay_ind["simulated_payments_excluded"] = demo_n

    events = [t.updated_at or t.created_at for t in completed + cancelled]
    return {
        "partner_type": "buyer",
        "partner_id": buyer_id,
        "name": b.company_name,
        "verification_status": b.verification_status,
        **_label(len(completed)),
        "transaction_history": {
            "completed": len(completed),
            "cancelled": len(cancelled),
            "in_progress": in_progress,
            "cancellation_note": "Cancellation cause is not recorded for transactions, so it is shown as a count, not a rate.",
        },
        "indicators": [terms_ind, pickup_ind, pay_ind],
        "complaints_and_disputes": _complaint_summary(db, "buyer", buyer_id),
        "recency": _recency(events, now),
        "ranking": _ranking(len(completed) >= MIN_COMPLETED_FOR_PROFILE,
                            [(tm_ok, tm_n), (pk_ok, pk_n)]),
    }


def _overdue(p, now: dt.datetime) -> bool:
    try:
        return bool(p.payment_due_date) and dt.date.fromisoformat(p.payment_due_date[:10]) < now.date()
    except ValueError:
        return False


def _paid_late(p) -> bool:
    try:
        return bool(p.payment_due_date and p.received_at
                    and p.received_at.date() > dt.date.fromisoformat(p.payment_due_date[:10]))
    except ValueError:
        return False


def _ranking(sufficient: bool, pairs: List[Tuple[int, int]]) -> Dict:
    """Pool every measured success/total pair and rank by the Wilson lower
    bound. Not a score shown to users -- only the sort key for ordering."""
    s = sum(a for a, n in pairs if n > 0)
    n = sum(n for _, n in pairs if n > 0)
    return {
        "eligible": bool(sufficient and n > 0),
        "evidence_points": n,
        "wilson_lower_bound": wilson_lower_bound(s, n) if (sufficient and n > 0) else None,
        "method": "95% Wilson lower bound over all measured indicators; "
                  "partners with insufficient history are listed after established ones, unranked.",
    }


def rank_profiles(profiles: List[Dict]) -> List[Dict]:
    """Established partners first (by lower bound, then evidence volume);
    insufficient-history partners after, ordered by volume only."""
    def key(p):
        r = p["ranking"]
        return (0 if r["eligible"] else 1,
                -(r["wilson_lower_bound"] or 0.0),
                -p["completed_outcomes"],
                p["partner_id"])
    ranked = sorted(profiles, key=key)
    pos = 0
    for p in ranked:
        if p["ranking"]["eligible"]:
            pos += 1
            p["ranking"]["position"] = pos
        else:
            p["ranking"]["position"] = None
    return ranked


def methodology() -> Dict:
    return {
        "principles": [
            "Every figure is computed from recorded transactions, trips and complaints; nothing is estimated or pre-filled.",
            "Each indicator shows its sample size and latest event date.",
            "Partners with too little history are labelled 'Insufficient history', never scored low.",
            "Evidence a partner has contested is left out of their rates while it is reviewed.",
            "Simulated (demo) payments are never counted.",
            "No composite score is shown; ranking uses a statistical lower bound so small samples cannot top the list.",
        ],
        "parameters": {
            "minimum_completed_outcomes": MIN_COMPLETED_FOR_PROFILE,
            "pickup_grace_hours": PICKUP_GRACE.total_seconds() / 3600,
            "quote_tolerance_percent": QUOTE_TOLERANCE_PCT,
            "recent_window_days": RECENT_WINDOW_DAYS,
        },
        "limitations": [
            "Buyer pickup and terms outcomes exist only where a farmer has recorded them.",
            "Final transport charge exists only where the farmer has recorded it.",
            "Reputation reflects CropWise activity only and is not a guarantee of future performance.",
        ],
    }
