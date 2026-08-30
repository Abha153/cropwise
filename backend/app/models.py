import datetime as dt

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, JSON,
    UniqueConstraint
)
from sqlalchemy.orm import relationship

from app.database import Base


def now():
    return dt.datetime.utcnow()


class Farmer(Base):
    __tablename__ = "farmers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    phone = Column(String, default="")
    location = Column(String, nullable=False)
    latitude = Column(Float, default=0.0)
    longitude = Column(Float, default=0.0)
    crops = Column(JSON, default=list)  # list of crop names the farmer grows
    preferred_language = Column(String, default="en")
    rating = Column(Float, default=4.5)
    fpo_group = Column(String, nullable=True)  # cooperative / FPO name if joined
    created_at = Column(DateTime, default=now)
    last_login = Column(DateTime, nullable=True)

    listings = relationship("CropListing", back_populates="farmer")
    notifications = relationship("Notification", back_populates="farmer")
    lots = relationship("Lot", back_populates="farmer")


class Buyer(Base):
    __tablename__ = "buyers"

    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    phone = Column(String, default="")
    location = Column(String, nullable=False)
    latitude = Column(Float, default=0.0)
    longitude = Column(Float, default=0.0)
    buyer_type = Column(String, default="wholesaler")  # wholesaler/retailer/processor/exporter/fpo
    verification_status = Column(String, default="pending")  # verified/pending -- new buyers start unverified; only the buyer-verification admin flow (or explicit seed data) should ever set this to "verified"
    reliability_score = Column(Float, default=85.0)  # 0-100
    payment_history_score = Column(Float, default=90.0)  # 0-100
    crops_of_interest = Column(JSON, default=list)
    preferred_language = Column(String, default="en")
    created_at = Column(DateTime, default=now)
    last_login = Column(DateTime, nullable=True)

    offers = relationship("BuyerOffer", back_populates="buyer")
    demands = relationship("BuyerDemand", back_populates="buyer")
    verification = relationship("BuyerVerification", back_populates="buyer", uselist=False)


class CropListing(Base):
    __tablename__ = "crop_listings"

    id = Column(Integer, primary_key=True, index=True)
    farmer_id = Column(Integer, ForeignKey("farmers.id"))
    crop = Column(String, nullable=False)
    quantity_kg = Column(Float, nullable=False)
    quality_grade = Column(String, default="B")  # A / B / C
    quality_score = Column(Float, default=75.0)
    expected_price_per_kg = Column(Float, nullable=False)
    location = Column(String, nullable=False)
    available_date = Column(String, nullable=False)  # ISO date string
    status = Column(String, default="active")  # active/sold/expired
    min_acceptable_price = Column(Float, nullable=True)
    bidding_deadline = Column(String, nullable=True)
    image_note = Column(String, nullable=True)
    note = Column(String, nullable=True)
    language = Column(String, default="en")
    created_at = Column(DateTime, default=now)

    farmer = relationship("Farmer", back_populates="listings")
    offers = relationship("BuyerOffer", back_populates="listing")


class BuyerOffer(Base):
    __tablename__ = "buyer_offers"

    id = Column(Integer, primary_key=True, index=True)
    buyer_id = Column(Integer, ForeignKey("buyers.id"))
    listing_id = Column(Integer, ForeignKey("crop_listings.id"), nullable=True)
    lot_id = Column(Integer, ForeignKey("lots.id"), nullable=True)
    buyer_demand_id = Column(Integer, ForeignKey("buyer_demands.id"), nullable=True)
    offered_price_per_kg = Column(Float, nullable=False)
    quantity_kg = Column(Float, nullable=False)
    message = Column(String, default="")
    language = Column(String, default="en")
    status = Column(String, default="pending")  # pending/accepted/rejected/withdrawn
    created_at = Column(DateTime, default=now)

    buyer = relationship("Buyer", back_populates="offers")
    listing = relationship("CropListing", back_populates="offers")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    listing_id = Column(Integer, ForeignKey("crop_listings.id"), nullable=True)
    lot_id = Column(Integer, ForeignKey("lots.id"), nullable=True)
    offer_id = Column(Integer, ForeignKey("buyer_offers.id"), nullable=True)
    farmer_id = Column(Integer, ForeignKey("farmers.id"))
    buyer_id = Column(Integer, ForeignKey("buyers.id"))
    final_price_per_kg = Column(Float, nullable=False)
    quantity_kg = Column(Float, nullable=False)
    total_amount = Column(Float, nullable=False)
    market_used = Column(String, default="")
    # Full lifecycle status (Phase 10)
    status = Column(String, default="OFFER_ACCEPTED")
    # Legacy -- kept for backward compat with old "completed" rows
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)

    events = relationship("TransactionEvent", back_populates="transaction")
    payments = relationship("Payment", back_populates="transaction")


class MarketPrice(Base):
    __tablename__ = "market_prices"

    id = Column(Integer, primary_key=True, index=True)
    crop = Column(String, index=True, nullable=False)
    market = Column(String, index=True, nullable=False)
    date = Column(String, nullable=False)
    min_price = Column(Float, nullable=False)
    max_price = Column(Float, nullable=False)
    modal_price = Column(Float, nullable=False)
    arrivals_tonnes = Column(Float, default=0.0)
    data_source = Column(String, default="demo", nullable=False)


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    farmer_id = Column(Integer, ForeignKey("farmers.id"), nullable=True)
    buyer_id = Column(Integer, ForeignKey("buyers.id"), nullable=True)
    type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    message = Column(String, nullable=False)
    severity = Column(String, default="info")  # info/warning/success
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=now)

    farmer = relationship("Farmer", back_populates="notifications")


class GroupSellingPool(Base):
    __tablename__ = "group_selling_pools"

    id = Column(Integer, primary_key=True, index=True)
    crop = Column(String, nullable=False)
    fpo_name = Column(String, nullable=False)
    status = Column(String, default="open")  # open/matched/closed
    created_at = Column(DateTime, default=now)

    memberships = relationship("GroupPoolMembership", back_populates="pool")

    @property
    def member_farmer_ids(self):
        return [m.farmer_id for m in self.memberships]

    @property
    def total_quantity_kg(self):
        return sum(m.quantity_kg for m in self.memberships)


class GroupPoolMembership(Base):
    __tablename__ = "group_pool_memberships"

    id = Column(Integer, primary_key=True, index=True)
    pool_id = Column(Integer, ForeignKey("group_selling_pools.id"))
    farmer_id = Column(Integer, ForeignKey("farmers.id"))
    quantity_kg = Column(Float, nullable=False)
    joined_at = Column(DateTime, default=now)

    pool = relationship("GroupSellingPool", back_populates="memberships")


class LoginEvent(Base):
    __tablename__ = "login_events"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True, index=True)
    role = Column(String, nullable=False, index=True)
    login_time = Column(DateTime, default=now, index=True)
    success = Column(Boolean, nullable=False, default=False, index=True)


# ============================================================
# NEW MODELS — Phase 1-15
# ============================================================

class BuyerDemand(Base):
    """Phase 1 — Buyer posts what they want to buy."""
    __tablename__ = "buyer_demands"

    id = Column(Integer, primary_key=True, index=True)
    buyer_id = Column(Integer, ForeignKey("buyers.id"), nullable=False)
    crop = Column(String, nullable=False, index=True)
    required_quantity_kg = Column(Float, nullable=False)
    minimum_quantity_kg = Column(Float, nullable=True)
    maximum_quantity_kg = Column(Float, nullable=True)
    target_price_per_kg = Column(Float, nullable=True)  # ₹/kg (not /quintal)
    quality_grade = Column(String, nullable=True)       # A/B/C
    moisture_limit = Column(Float, nullable=True)       # %
    foreign_matter_limit = Column(Float, nullable=True) # %
    damaged_grains_limit = Column(Float, nullable=True) # %
    delivery_location = Column(String, nullable=True)
    delivery_latitude = Column(Float, nullable=True)
    delivery_longitude = Column(Float, nullable=True)
    delivery_deadline = Column(String, nullable=True)   # ISO date string
    payment_terms = Column(String, nullable=True)       # e.g. "Advance 50%, rest on delivery"
    additional_requirements = Column(Text, nullable=True)
    status = Column(String, default="ACTIVE", index=True)
    # ACTIVE / PARTIALLY_FILLED / FULFILLED / EXPIRED / CANCELLED
    expires_at = Column(String, nullable=True)          # ISO date string
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)

    buyer = relationship("Buyer", back_populates="demands")


class BuyerVerification(Base):
    """Phase 2 — Platform document-based buyer verification."""
    __tablename__ = "buyer_verifications"

    id = Column(Integer, primary_key=True, index=True)
    buyer_id = Column(Integer, ForeignKey("buyers.id"), nullable=False, unique=True)
    business_name = Column(String, nullable=True)
    business_registration_number = Column(String, nullable=True)
    gst_number = Column(String, nullable=True)
    license_number = Column(String, nullable=True)
    document_urls = Column(JSON, default=list)
    # PENDING / UNDER_REVIEW / VERIFIED / REJECTED / SUSPENDED
    verification_status = Column(String, default="PENDING")
    # PLATFORM_VERIFIED / DOCUMENT_VERIFIED / SELF_DECLARED / PENDING
    verification_method = Column(String, default="SELF_DECLARED")
    verification_notes = Column(Text, nullable=True)
    verified_at = Column(DateTime, nullable=True)
    rejected_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)

    buyer = relationship("Buyer", back_populates="verification")


class Lot(Base):
    """Phase 4 — Proper agricultural lot (extends / wraps CropListing concept)."""
    __tablename__ = "lots"

    id = Column(Integer, primary_key=True, index=True)
    lot_number = Column(String, unique=True, nullable=False, index=True)
    farmer_id = Column(Integer, ForeignKey("farmers.id"), nullable=False)
    fpo_id = Column(Integer, ForeignKey("group_selling_pools.id"), nullable=True)
    listing_id = Column(Integer, ForeignKey("crop_listings.id"), nullable=True)
    crop = Column(String, nullable=False, index=True)
    quantity_kg = Column(Float, nullable=False)
    grade = Column(String, default="B")
    quality_score = Column(Float, default=75.0)
    quality_report = Column(JSON, nullable=True)  # full AI report
    harvest_date = Column(String, nullable=True)
    available_date = Column(String, nullable=True)
    location = Column(String, nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    expected_price = Column(Float, nullable=False)       # ₹/kg
    minimum_price = Column(Float, nullable=True)         # ₹/kg
    # DRAFT / AVAILABLE / UNDER_OFFER / SOLD / IN_TRANSIT / DELIVERED / CANCELLED
    status = Column(String, default="AVAILABLE", index=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)

    farmer = relationship("Farmer", back_populates="lots")


class StorageFacility(Base):
    """Phase 6 — Storage facilities (warehouses, cold storage, etc.)."""
    __tablename__ = "storage_facilities"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    # WAREHOUSE / COLD_STORAGE / FPO_STORAGE / PRIVATE_STORAGE / GOVERNMENT_STORAGE
    facility_type = Column(String, default="WAREHOUSE")
    location = Column(String, nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    capacity_kg = Column(Float, nullable=False)
    available_capacity_kg = Column(Float, nullable=False)
    price_per_kg_per_day = Column(Float, nullable=False)
    crop_types = Column(JSON, default=list)
    temperature_controlled = Column(Boolean, default=False)
    warehouse_features = Column(JSON, default=list)
    quality_services = Column(JSON, default=list)
    contact = Column(String, nullable=True)
    # VERIFIED / UNVERIFIED / DEMO
    verification_status = Column(String, default="DEMO")
    # ACTIVE / INACTIVE
    status = Column(String, default="ACTIVE")
    is_demo = Column(Boolean, default=True)
    created_at = Column(DateTime, default=now)

    bookings = relationship("StorageBooking", back_populates="facility")


class StorageBooking(Base):
    """Phase 6 — Farmer books storage for a lot."""
    __tablename__ = "storage_bookings"

    id = Column(Integer, primary_key=True, index=True)
    farmer_id = Column(Integer, ForeignKey("farmers.id"), nullable=False)
    storage_facility_id = Column(Integer, ForeignKey("storage_facilities.id"), nullable=False)
    lot_id = Column(Integer, ForeignKey("lots.id"), nullable=True)
    quantity_kg = Column(Float, nullable=False)
    start_date = Column(String, nullable=False)
    end_date = Column(String, nullable=True)
    estimated_cost = Column(Float, nullable=True)
    # REQUESTED / CONFIRMED / ACTIVE / COMPLETED / CANCELLED
    status = Column(String, default="REQUESTED")
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)

    facility = relationship("StorageFacility", back_populates="bookings")


class TransportRequest(Base):
    """Phase 9 — Logistics coordination for a lot."""
    __tablename__ = "transport_requests"

    id = Column(Integer, primary_key=True, index=True)
    lot_id = Column(Integer, ForeignKey("lots.id"), nullable=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=True)
    farmer_id = Column(Integer, ForeignKey("farmers.id"), nullable=False)
    buyer_id = Column(Integer, ForeignKey("buyers.id"), nullable=True)
    pickup_location = Column(String, nullable=False)
    destination = Column(String, nullable=False)
    pickup_date = Column(String, nullable=True)
    pickup_time = Column(String, nullable=True)
    vehicle_type = Column(String, nullable=True)
    driver_name = Column(String, nullable=True)
    driver_contact = Column(String, nullable=True)
    vehicle_capacity = Column(Float, nullable=True)
    estimated_cost = Column(Float, nullable=True)
    shared_transport = Column(Boolean, default=False)
    quantity_kg = Column(Float, nullable=True)
    # REQUESTED / MATCHED / CONFIRMED / PICKED_UP / IN_TRANSIT / DELIVERED / CANCELLED
    status = Column(String, default="REQUESTED")
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)


class Payment(Base):
    """Phase 11 — Payment tracking."""
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False)
    buyer_id = Column(Integer, ForeignKey("buyers.id"), nullable=False)
    farmer_id = Column(Integer, ForeignKey("farmers.id"), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String, default="INR")
    # PENDING / DUE / INITIATED / PAID / FAILED / DISPUTED
    payment_status = Column(String, default="PENDING")
    payment_method = Column(String, nullable=True)   # UPI/NEFT/Cash/etc.
    payment_reference = Column(String, nullable=True)
    payment_due_date = Column(String, nullable=True)
    initiated_at = Column(DateTime, nullable=True)
    received_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    is_demo = Column(Boolean, default=True)
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)

    transaction = relationship("Transaction", back_populates="payments")


class TransactionEvent(Base):
    """Phase 12 — Transparent event trail for every transaction."""
    __tablename__ = "transaction_events"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False)
    event_type = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    performed_by = Column(String, nullable=True)   # "farmer" / "buyer" / "admin" / "system"
    performed_by_id = Column(Integer, nullable=True)
    event_metadata = Column("metadata", JSON, nullable=True)
    created_at = Column(DateTime, default=now)

    transaction = relationship("Transaction", back_populates="events")


class Grievance(Base):
    """Phase 13 — Dispute / grievance system."""
    __tablename__ = "grievances"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=True)
    raised_by = Column(String, nullable=False)       # "farmer" / "buyer"
    raised_by_id = Column(Integer, nullable=False)
    against_user = Column(String, nullable=True)     # "farmer" / "buyer"
    against_user_id = Column(Integer, nullable=True)
    # PAYMENT / QUALITY / QUANTITY / PRICE / DELIVERY / LOGISTICS / BUYER / FARMER / OTHER
    category = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    evidence_urls = Column(JSON, default=list)
    # OPEN / UNDER_REVIEW / WAITING_FOR_EVIDENCE / RESOLVED / REJECTED / CLOSED
    status = Column(String, default="OPEN")
    priority = Column(String, default="MEDIUM")   # LOW / MEDIUM / HIGH
    assigned_to = Column(String, nullable=True)
    resolution = Column(Text, nullable=True)
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)
    resolved_at = Column(DateTime, nullable=True)


class Rating(Base):
    """Phase 14 — Mutual ratings after completed transactions."""
    __tablename__ = "ratings"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False)
    rater_role = Column(String, nullable=False)    # "farmer" / "buyer"
    rater_id = Column(Integer, nullable=False)
    ratee_role = Column(String, nullable=False)    # "farmer" / "buyer"
    ratee_id = Column(Integer, nullable=False)
    rating = Column(Float, nullable=False)         # 1.0 – 5.0
    review = Column(Text, nullable=True)
    created_at = Column(DateTime, default=now)

    __table_args__ = (
        UniqueConstraint("transaction_id", "rater_role", "rater_id", name="uq_rating_per_txn"),
    )
