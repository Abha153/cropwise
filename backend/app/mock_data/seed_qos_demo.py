"""
Demo seed data for the partner reputation / QoS feature.

Creates 12 partners (6 buyers, 6 transport agencies) whose *evidence* (trips,
transactions, farmer-recorded outcomes, final charges, delivery promises,
cancellations, disputes) is designed so every state in the reputation UI
appears at least once. Nothing here writes a score: the profiles are still
computed by app/services/reputation.py from these rows.

Run from backend/:
    python -m app.mock_data.seed_qos_demo            # seed
    python -m app.mock_data.seed_qos_demo --reset    # remove everything it created

Re-using the public demo accounts (password demo1234):
    farmers : ramesh / sunita / manoj @cropwise.demo   (re-used if they exist)
    buyers  : agriexport / freshfoods / greenbasket @cropwise.demo (re-used)
New partners use e-mails @seed-qos.demo with the same password.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path
from typing import Dict, List

from app import models

SEED_DOMAIN = "seed-qos.demo"
DEMO_PASSWORD = "demo1234"
MANIFEST = Path(__file__).resolve().parents[2] / ".seed_qos_manifest.json"
IST = dt.timedelta(hours=5, minutes=30)

FARMER_EMAILS = [
    ("Ramesh Patel", "ramesh@cropwise.demo"),
    ("Sunita Devi", "sunita@cropwise.demo"),
    ("Manoj Verma", "manoj@cropwise.demo"),
]

ROUTES = [("Bilaspur", "Raipur"), ("Bilaspur", "Nagpur"), ("Korba", "Raipur"), ("Durg", "Nagpur")]

# ── transport agencies ───────────────────────────────────────────────────────
# n delivered trips. *_fail = trip indexes that fail that indicator.
# promise=False -> no delivery promise recorded (on-time delivery "not recorded").
# no_final = trip indexes with no final charge recorded yet.
TRANSPORTERS = [
    dict(key="shakti", name="Shakti Logistics", n=14, span=(80, 4),
         pickup_fail={9}, delivery_fail={11}, quote_fail={5, 12}),
    dict(key="bilaspur", name="Bilaspur Roadways", n=10, span=(78, 5),
         pickup_fail=set(), delivery_fail={3}, quote_fail=set()),
    dict(key="mahakoshal", name="Mahakoshal Carriers", n=7, span=(85, 45),
         pickup_fail={4, 5, 6}, delivery_fail={4, 5, 6}, quote_fail={3, 4, 5, 6}),
    dict(key="cargolink", name="Chhattisgarh Cargo Link", n=8, span=(75, 6), promise=False,
         pickup_fail={2}, delivery_fail=set(), quote_fail={6}),
    dict(key="rapid", name="Rapid Agri Haulers", n=5, span=(60, 8),
         pickup_fail={2}, delivery_fail={3}, quote_fail=set(),
         cancels=[("transporter", 24), ("transporter", 14), ("farmer", 19), (None, 30)]),
    dict(key="vidarbha", name="Vidarbha Movers", n=2, span=(8, 3),
         pickup_fail=set(), delivery_fail=set(), quote_fail=set(), no_final={1}),
]

# ── buyers ───────────────────────────────────────────────────────────────────
# n COMPLETED transactions. record_* = whether the farmer recorded that outcome.
BUYERS = [
    dict(key="agriexport", email="agriexport@cropwise.demo", company="AgriExport", n=15, span=(85, 3),
         pickup_result={14: "LATE"}, terms_fail=set()),
    dict(key="freshfoods", email="freshfoods@cropwise.demo", company="FreshFoods", n=12, span=(80, 4),
         pickup_result={7: "LATE"}, terms_fail={4}, extra_delivered=True),
    dict(key="greenbasket", email="greenbasket@cropwise.demo", company="GreenBasket", n=9, span=(70, 6),
         pickup_result={6: "LATE"}, terms_fail={2, 5}),
    dict(key="kisan", email=f"kisan-mandi@{SEED_DOMAIN}", company="Kisan Mandi Co.", n=8, span=(75, 10),
         pickup_result={1: "LATE", 3: "LATE", 4: "NO_SHOW", 6: "LATE"}, terms_fail={0, 2, 5}, legacy_score=90.0),
    dict(key="raipurhub", email=f"raipur-fresh-hub@{SEED_DOMAIN}", company="Raipur Fresh Hub", n=6, span=(60, 9),
         record_pickup=False, record_terms=False),
    dict(key="nagpur", email=f"nagpur-agro@{SEED_DOMAIN}", company="Nagpur Agro Traders", n=2, span=(14, 5),
         pickup_result={}, terms_fail=set()),
]

# ── disputes: one per status ─────────────────────────────────────────────────
DISPUTES = [
    dict(kind="record", buyer="kisan", metric="BUYER_PICKUP", idx=4, status="OPEN", days_ago=5,
         reason="Our truck was at the farm gate on time; the farmer was not present to load.", admin_note=None),
    dict(kind="record", buyer="greenbasket", metric="BUYER_TERMS", idx=5, status="UNDER_REVIEW", days_ago=9,
         reason="Quality grade was downgraded at weighing in front of the farmer's representative.",
         admin_note="Asked the buyer for the weighing slip."),
    dict(kind="trip", transporter="mahakoshal", idx=6, status="UPHELD", days_ago=40,
         reason="Road closure on NH-30 caused the delay; the farmer agreed to a new date by phone.",
         admin_note="Closure notice verified; the trip is excluded from this agency's rates."),
    dict(kind="trip", transporter="shakti", idx=5, status="REJECTED", days_ago=60,
         reason="The extra amount covered a toll that was agreed verbally.",
         admin_note="The agreement shows no toll clause; the charge stays in the record."),
]


# ── helpers ──────────────────────────────────────────────────────────────────
def _hash(password: str) -> str:
    from app import auth_utils
    for name in ("hash_password", "get_password_hash", "hash_pw"):
        fn = getattr(auth_utils, name, None)
        if callable(fn):
            return fn(password)
    from passlib.context import CryptContext
    return CryptContext(schemes=["bcrypt"], deprecated="auto").hash(password)


def _spread(i: int, n: int, start: int, end: int) -> int:
    """Days ago for item i of n, spread evenly from `start` to `end` days ago."""
    return end if n <= 1 else start - round(i * (start - end) / (n - 1))


def _add(db, obj, bucket: List[int]):
    db.add(obj)
    db.flush()
    bucket.append(obj.id)
    return obj


def seed(db, now: dt.datetime = None) -> Dict[str, List[int]]:
    """Insert the demo evidence. Returns {table: [ids created]} for reset()."""
    now = now or dt.datetime.utcnow()
    if db.query(models.Transporter).filter(models.Transporter.email.like(f"%@{SEED_DOMAIN}")).first():
        raise RuntimeError("QoS demo data is already present; run with --reset first.")
    m: Dict[str, List[int]] = {k: [] for k in
                               ("farmers", "buyers", "transporters", "transactions", "records", "trips", "disputes")}
    pw = _hash(DEMO_PASSWORD)

    # farmers (re-use the public demo farmers when they exist)
    farmers = []
    for name, email in FARMER_EMAILS:
        f = db.query(models.Farmer).filter(models.Farmer.email == email).first()
        if not f:
            f = _add(db, models.Farmer(name=name, email=email, password_hash=pw, location="Bilaspur"), m["farmers"])
        farmers.append(f)

    # transport agencies + trips
    trips: Dict[tuple, models.TransportRequest] = {}
    transporters = {}
    for spec in TRANSPORTERS:
        kw = dict(name=spec["name"], email=f"{spec['key']}@{SEED_DOMAIN}", password_hash=pw)
        if hasattr(models.Transporter, "business_name"):
            kw["business_name"] = spec["name"]
        t = _add(db, models.Transporter(**kw), m["transporters"])
        transporters[spec["key"]] = t
        n = spec["n"]
        for i in range(n):
            day = (now - dt.timedelta(days=_spread(i, n, *spec["span"]))).date()
            sched = dt.datetime.combine(day, dt.time(10, 0)) - IST          # 10:00 IST
            late_pickup = i in spec["pickup_fail"]
            picked = sched + (dt.timedelta(hours=5) if late_pickup else dt.timedelta(minutes=20))
            delivered = picked + dt.timedelta(days=1)
            promise = None
            if spec.get("promise", True):
                promise = (day if i in spec["delivery_fail"] else day + dt.timedelta(days=1)).isoformat()
            agreed = 3200 + 150 * (i % 6)
            final = None
            if i not in spec.get("no_final", set()):
                final = round(agreed * 1.25) if i in spec["quote_fail"] else (agreed if i % 2 == 0 else round(agreed * 1.03))
            a, b = ROUTES[i % len(ROUTES)]
            trips[(spec["key"], i)] = _add(db, models.TransportRequest(
                farmer_id=farmers[i % len(farmers)].id, transporter_id=t.id,
                pickup_location=a, destination=b, status="DELIVERED",
                pickup_date=day.isoformat(), pickup_time="10:00",
                picked_up_at=picked, delivered_at=delivered, promised_delivery_by=promise,
                transporter_agreed_price=agreed, final_charge=final,
                final_charge_recorded_at=(delivered + dt.timedelta(hours=6)) if final is not None else None,
                created_at=picked - dt.timedelta(days=3)), m["trips"])
        for j, (by, ago) in enumerate(spec.get("cancels", [])):
            day = (now - dt.timedelta(days=ago)).date()
            a, b = ROUTES[j % len(ROUTES)]
            _add(db, models.TransportRequest(
                farmer_id=farmers[j % len(farmers)].id, transporter_id=t.id,
                pickup_location=a, destination=b, status="CANCELLED",
                pickup_date=day.isoformat(), pickup_time="10:00", transporter_agreed_price=3400,
                cancelled_by=by, cancelled_at=(now - dt.timedelta(days=ago + 1)) if by else None,
                created_at=now - dt.timedelta(days=ago + 4)), m["trips"])

    # buyers + transactions + farmer-recorded outcomes
    buyers = {}
    records: Dict[tuple, models.PerformanceRecord] = {}
    for spec in BUYERS:
        b = db.query(models.Buyer).filter(models.Buyer.email == spec["email"]).first()
        if not b:
            extra = {}
            if "legacy_score" in spec:      # legacy seeded columns: shown to be ignored
                extra = dict(reliability_score=spec["legacy_score"], payment_history_score=spec["legacy_score"])
            b = _add(db, models.Buyer(company_name=spec["company"], email=spec["email"], password_hash=pw,
                                      location="Raipur", **extra), m["buyers"])
        buyers[spec["key"]] = b
        n = spec["n"]
        for i in range(n):
            created = now - dt.timedelta(days=_spread(i, n, *spec["span"]))
            ppk, qty = 18 + (i % 5), 500 + 100 * (i % 4)
            farmer = farmers[i % len(farmers)]
            txn = _add(db, models.Transaction(
                farmer_id=farmer.id, buyer_id=b.id, final_price_per_kg=ppk, quantity_kg=qty,
                total_amount=ppk * qty, status="COMPLETED", created_at=created,
                updated_at=created + dt.timedelta(days=2)), m["transactions"])
            for metric, flag in (("BUYER_PICKUP", "record_pickup"), ("BUYER_TERMS", "record_terms")):
                if not spec.get(flag, True):
                    continue
                if metric == "BUYER_PICKUP":
                    result = spec["pickup_result"].get(i, "ON_TIME")
                else:
                    result = "DEVIATED" if i in spec["terms_fail"] else "AS_AGREED"
                records[(spec["key"], metric, i)] = _add(db, models.PerformanceRecord(
                    subject_role="buyer", subject_id=b.id, transaction_id=txn.id, metric=metric, result=result,
                    recorded_by_role="farmer", recorded_by_id=farmer.id,
                    created_at=created + dt.timedelta(days=1)), m["records"])
        if spec.get("extra_delivered"):      # live-demo item: farmer can record the outcome in the UI
            _add(db, models.Transaction(
                farmer_id=farmers[0].id, buyer_id=b.id, final_price_per_kg=21, quantity_kg=800,
                total_amount=21 * 800, status="DELIVERED", created_at=now - dt.timedelta(days=2),
                updated_at=now - dt.timedelta(days=1)), m["transactions"])

    # disputes (one per status)
    for d in DISPUTES:
        if d["kind"] == "record":
            subject, target_type = buyers[d["buyer"]], "PERFORMANCE_RECORD"
            target = records[(d["buyer"], d["metric"], d["idx"])]
            role = "buyer"
        else:
            subject, target_type = transporters[d["transporter"]], "TRANSPORT_REQUEST"
            target = trips[(d["transporter"], d["idx"])]
            role = "transporter"
        created = now - dt.timedelta(days=d["days_ago"])
        decided = d["status"] in ("UPHELD", "REJECTED")
        _add(db, models.ReputationDispute(
            subject_role=role, subject_id=subject.id, target_type=target_type, target_id=target.id,
            reason=d["reason"], evidence_urls=[], status=d["status"], admin_note=d["admin_note"],
            created_at=created, updated_at=created + dt.timedelta(days=2),
            resolved_at=(created + dt.timedelta(days=2)) if decided else None), m["disputes"])

    db.commit()
    return m


def reset(db, manifest: Dict[str, List[int]]) -> None:
    """Delete everything seed() created (and outcomes users added to seeded transactions)."""
    def ids(k):
        return manifest.get(k, [])
    db.query(models.ReputationDispute).filter(models.ReputationDispute.id.in_(ids("disputes"))).delete(synchronize_session=False)
    db.query(models.PerformanceRecord).filter(models.PerformanceRecord.transaction_id.in_(ids("transactions"))).delete(synchronize_session=False)
    db.query(models.TransportRequest).filter(models.TransportRequest.id.in_(ids("trips"))).delete(synchronize_session=False)
    db.query(models.Transaction).filter(models.Transaction.id.in_(ids("transactions"))).delete(synchronize_session=False)
    db.query(models.Buyer).filter(models.Buyer.id.in_(ids("buyers"))).delete(synchronize_session=False)
    db.query(models.Transporter).filter(models.Transporter.id.in_(ids("transporters"))).delete(synchronize_session=False)
    db.query(models.Farmer).filter(models.Farmer.id.in_(ids("farmers"))).delete(synchronize_session=False)
    db.commit()


EXPECTED = """\
Expected profiles (after seeding)
  Buyers                    completed  pickup     terms      note
  AgriExport                15         14 of 15   15 of 15   strongest
  FreshFoods                12         11 of 12   11 of 12   +1 delivered txn with no outcome recorded (try it as farmer)
  GreenBasket               9          8 of 9     7 of 8     1 deviated record under review (not counted)
  Kisan Mandi Co.           8          4 of 7     5 of 8     no-show contested (open); legacy score 90 is ignored
  Raipur Fresh Hub          6          not rec.   not rec.   established but nothing recorded
  Nagpur Agro Traders       2          2 of 2     2 of 2     Insufficient history
  Transport agencies        trips      pickup     delivery   quote      fulfilment
  Shakti Logistics          14         13 of 14   13 of 14   12 of 14   14 of 14  (rejected dispute: still counts)
  Bilaspur Roadways         10         10 of 10   9 of 10    10 of 10   10 of 10
  Mahakoshal Carriers       6 (+1)     4 of 6     4 of 6     3 of 6     6 of 6    (upheld dispute: 1 trip excluded)
  Chhattisgarh Cargo Link   8          7 of 8     not rec.   7 of 8     8 of 8    (no delivery promise)
  Rapid Agri Haulers        5          4 of 5     4 of 5     5 of 5     5 of 7    (2 agency cancellations)
  Vidarbha Movers           2          2 of 2     2 of 2     1 of 1     2 of 2    Insufficient history; 1 trip has no final charge yet
"""


def main(argv: List[str]) -> int:
    from app.database import Base, engine, get_db, run_lightweight_migrations
    Base.metadata.create_all(bind=engine)
    run_lightweight_migrations()
    db = next(get_db())
    try:
        if "--reset" in argv:
            if not MANIFEST.exists():
                print("Nothing to reset (no manifest found).")
                return 0
            reset(db, json.loads(MANIFEST.read_text()))
            MANIFEST.unlink()
            print("QoS demo data removed.")
            return 0
        if MANIFEST.exists():
            print("Already seeded. Run with --reset to remove it first.")
            return 1
        manifest = seed(db)
        MANIFEST.write_text(json.dumps(manifest))
        print("Seeded: " + ", ".join(f"{len(v)} {k}" for k, v in manifest.items()))
        print(EXPECTED)
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
