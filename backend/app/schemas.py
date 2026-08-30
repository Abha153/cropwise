import datetime as dt
from typing import Optional, List, Any

from pydantic import BaseModel, EmailStr, ConfigDict


# ---------- Auth ----------

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user: dict


class FarmerRegister(BaseModel):
    name: str
    email: EmailStr
    password: str
    phone: Optional[str] = ""
    location: str
    latitude: float = 0.0
    longitude: float = 0.0
    crops: List[str] = []
    preferred_language: str = "en"


class BuyerRegister(BaseModel):
    company_name: str
    email: EmailStr
    password: str
    phone: Optional[str] = ""
    location: str
    latitude: float = 0.0
    longitude: float = 0.0
    buyer_type: str = "wholesaler"
    crops_of_interest: List[str] = []
    preferred_language: str = "en"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# ---------- Farmer / Buyer ----------

class FarmerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: str
    phone: str
    location: str
    latitude: float
    longitude: float
    crops: List[str]
    preferred_language: str
    rating: float
    fpo_group: Optional[str] = None
    created_at: dt.datetime
    last_login: Optional[dt.datetime] = None


class FarmerUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    crops: Optional[List[str]] = None
    preferred_language: Optional[str] = None


class BuyerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    company_name: str
    email: str
    phone: str
    location: str
    latitude: float
    longitude: float
    buyer_type: str
    verification_status: str
    reliability_score: float
    payment_history_score: float
    crops_of_interest: List[str]
    preferred_language: str
    created_at: dt.datetime
    last_login: Optional[dt.datetime] = None


# ---------- Public-safe profiles ----------

class FarmerPublicOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    location: str
    crops: List[str]
    rating: float
    fpo_group: Optional[str] = None


class BuyerPublicOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    company_name: str
    location: str
    buyer_type: str
    verification_status: str
    reliability_score: float
    crops_of_interest: List[str]


# ---------- Listings ----------

class ListingCreate(BaseModel):
    crop: str
    quantity_kg: float
    quality_grade: str = "B"
    quality_score: float = 75.0
    expected_price_per_kg: float
    location: Optional[str] = None
    available_date: str
    min_acceptable_price: Optional[float] = None
    bidding_deadline: Optional[str] = None
    image_note: Optional[str] = None
    note: Optional[str] = None
    language: str = "en"


class ListingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    farmer_id: int
    crop: str
    quantity_kg: float
    quality_grade: str
    quality_score: float
    expected_price_per_kg: float
    location: str
    available_date: str
    status: str
    min_acceptable_price: Optional[float]
    bidding_deadline: Optional[str]
    image_note: Optional[str]
    note: Optional[str] = None
    language: str = "en"
    created_at: dt.datetime


# ---------- Offers ----------

class OfferCreate(BaseModel):
    listing_id: Optional[int] = None
    lot_id: Optional[int] = None
    buyer_demand_id: Optional[int] = None
    offered_price_per_kg: float
    quantity_kg: float
    message: Optional[str] = ""
    language: str = "en"


class OfferOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    buyer_id: int
    listing_id: Optional[int] = None
    lot_id: Optional[int] = None
    buyer_demand_id: Optional[int] = None
    offered_price_per_kg: float
    quantity_kg: float
    message: str
    language: str = "en"
    status: str
    created_at: dt.datetime


# ---------- Advisor ----------

class AdvisorRequest(BaseModel):
    crop: str
    quantity_kg: float
    quality_grade: str = "B"
    location: str
    harvest_date: Optional[str] = None


# ---------- Profit calculator ----------

class ProfitScenario(BaseModel):
    label: str
    crop: str
    quantity_kg: float
    selling_price_per_kg: float
    transport_cost: float = 0.0
    labour_cost: float = 0.0
    packaging_cost: float = 0.0
    storage_cost: float = 0.0
    other_cost: float = 0.0


class ProfitCompareRequest(BaseModel):
    scenarios: List[ProfitScenario]


# ---------- Group selling ----------

class GroupSellingJoin(BaseModel):
    crop: str
    quantity_kg: float
    fpo_name: Optional[str] = "Independent Growers Collective"


# ---------- FarmPool ----------

class FarmPoolRequest(BaseModel):
    crop: str
    location: str
    quantity_kg: float
    destination_market: Optional[str] = None


# ---------- Assistant ----------

class AssistantAsk(BaseModel):
    question: str
    language: str = "en"
    known_crop: Optional[str] = None
    known_quantity_kg: Optional[float] = None
    known_location: Optional[str] = None


# ---------- Quality grading ----------

class QualityGradeRequest(BaseModel):
    crop: str
    image_name: Optional[str] = None


# ---------- Buyer Demand (Phase 1) ----------

class BuyerDemandCreate(BaseModel):
    crop: str
    required_quantity_kg: float
    minimum_quantity_kg: Optional[float] = None
    maximum_quantity_kg: Optional[float] = None
    target_price_per_kg: Optional[float] = None
    quality_grade: Optional[str] = None
    moisture_limit: Optional[float] = None
    foreign_matter_limit: Optional[float] = None
    damaged_grains_limit: Optional[float] = None
    delivery_location: Optional[str] = None
    delivery_latitude: Optional[float] = None
    delivery_longitude: Optional[float] = None
    delivery_deadline: Optional[str] = None
    payment_terms: Optional[str] = None
    additional_requirements: Optional[str] = None
    expires_at: Optional[str] = None


class BuyerDemandUpdate(BaseModel):
    required_quantity_kg: Optional[float] = None
    minimum_quantity_kg: Optional[float] = None
    maximum_quantity_kg: Optional[float] = None
    target_price_per_kg: Optional[float] = None
    quality_grade: Optional[str] = None
    moisture_limit: Optional[float] = None
    foreign_matter_limit: Optional[float] = None
    damaged_grains_limit: Optional[float] = None
    delivery_location: Optional[str] = None
    delivery_deadline: Optional[str] = None
    payment_terms: Optional[str] = None
    additional_requirements: Optional[str] = None
    expires_at: Optional[str] = None
    status: Optional[str] = None


class BuyerDemandOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    buyer_id: int
    crop: str
    required_quantity_kg: float
    minimum_quantity_kg: Optional[float]
    maximum_quantity_kg: Optional[float]
    target_price_per_kg: Optional[float]
    quality_grade: Optional[str]
    moisture_limit: Optional[float]
    foreign_matter_limit: Optional[float]
    damaged_grains_limit: Optional[float]
    delivery_location: Optional[str]
    delivery_latitude: Optional[float]
    delivery_longitude: Optional[float]
    delivery_deadline: Optional[str]
    payment_terms: Optional[str]
    additional_requirements: Optional[str]
    status: str
    expires_at: Optional[str]
    created_at: dt.datetime
    updated_at: dt.datetime


# ---------- Buyer Verification (Phase 2) ----------

class BuyerVerificationCreate(BaseModel):
    business_name: Optional[str] = None
    business_registration_number: Optional[str] = None
    gst_number: Optional[str] = None
    license_number: Optional[str] = None
    document_urls: List[str] = []


class BuyerVerificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    buyer_id: int
    business_name: Optional[str]
    business_registration_number: Optional[str]
    gst_number: Optional[str]
    license_number: Optional[str]
    document_urls: List[str]
    verification_status: str
    verification_method: str
    verification_notes: Optional[str]
    verified_at: Optional[dt.datetime]
    rejected_reason: Optional[str]
    created_at: dt.datetime
    updated_at: dt.datetime


# ---------- Lot (Phase 4) ----------

class LotCreate(BaseModel):
    crop: str
    quantity_kg: float
    grade: str = "B"
    quality_score: float = 75.0
    quality_report: Optional[Any] = None
    harvest_date: Optional[str] = None
    available_date: Optional[str] = None
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    expected_price: float
    minimum_price: Optional[float] = None
    note: Optional[str] = None
    fpo_id: Optional[int] = None
    listing_id: Optional[int] = None


class LotUpdate(BaseModel):
    quantity_kg: Optional[float] = None
    grade: Optional[str] = None
    quality_score: Optional[float] = None
    expected_price: Optional[float] = None
    minimum_price: Optional[float] = None
    available_date: Optional[str] = None
    status: Optional[str] = None
    note: Optional[str] = None


class LotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    lot_number: str
    farmer_id: int
    fpo_id: Optional[int]
    listing_id: Optional[int]
    crop: str
    quantity_kg: float
    grade: str
    quality_score: float
    quality_report: Optional[Any]
    harvest_date: Optional[str]
    available_date: Optional[str]
    location: str
    latitude: Optional[float]
    longitude: Optional[float]
    expected_price: float
    minimum_price: Optional[float]
    status: str
    note: Optional[str]
    created_at: dt.datetime
    updated_at: dt.datetime


# ---------- Storage (Phase 6) ----------

class StorageFacilityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    facility_type: str
    location: str
    latitude: Optional[float]
    longitude: Optional[float]
    capacity_kg: float
    available_capacity_kg: float
    price_per_kg_per_day: float
    crop_types: List[str]
    temperature_controlled: bool
    warehouse_features: List[str]
    quality_services: List[str]
    contact: Optional[str]
    verification_status: str
    status: str
    is_demo: bool
    created_at: dt.datetime


class StorageBookingCreate(BaseModel):
    storage_facility_id: int
    lot_id: Optional[int] = None
    quantity_kg: float
    start_date: str
    end_date: Optional[str] = None


class StorageBookingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    farmer_id: int
    storage_facility_id: int
    lot_id: Optional[int]
    quantity_kg: float
    start_date: str
    end_date: Optional[str]
    estimated_cost: Optional[float]
    status: str
    created_at: dt.datetime
    updated_at: dt.datetime


# ---------- Transport (Phase 9) ----------

class TransportRequestCreate(BaseModel):
    lot_id: Optional[int] = None
    buyer_id: Optional[int] = None
    pickup_location: str
    destination: str
    pickup_date: Optional[str] = None
    pickup_time: Optional[str] = None
    vehicle_type: Optional[str] = None
    quantity_kg: Optional[float] = None
    shared_transport: bool = False


class TransportRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    lot_id: Optional[int]
    farmer_id: int
    buyer_id: Optional[int]
    pickup_location: str
    destination: str
    pickup_date: Optional[str]
    pickup_time: Optional[str]
    vehicle_type: Optional[str]
    driver_name: Optional[str]
    driver_contact: Optional[str]
    vehicle_capacity: Optional[float]
    estimated_cost: Optional[float]
    shared_transport: bool
    quantity_kg: Optional[float]
    status: str
    created_at: dt.datetime
    updated_at: dt.datetime


# ---------- Transaction (Phase 10) ----------

class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    listing_id: Optional[int]
    lot_id: Optional[int]
    offer_id: Optional[int]
    farmer_id: int
    buyer_id: int
    final_price_per_kg: float
    quantity_kg: float
    total_amount: float
    market_used: str
    status: str
    created_at: dt.datetime


class TransactionStatusUpdate(BaseModel):
    status: str


# ---------- Payment (Phase 11) ----------

class PaymentCreate(BaseModel):
    transaction_id: int
    amount: float
    payment_method: Optional[str] = None
    notes: Optional[str] = None
    payment_due_date: Optional[str] = None


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    transaction_id: int
    buyer_id: int
    farmer_id: int
    amount: float
    currency: str
    payment_status: str
    payment_method: Optional[str]
    payment_reference: Optional[str]
    payment_due_date: Optional[str]
    initiated_at: Optional[dt.datetime]
    received_at: Optional[dt.datetime]
    notes: Optional[str]
    is_demo: bool
    created_at: dt.datetime
    updated_at: dt.datetime


# ---------- Transaction Events (Phase 12) ----------

class TransactionEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    transaction_id: int
    event_type: str
    description: Optional[str]
    performed_by: Optional[str]
    performed_by_id: Optional[int]
    event_metadata: Optional[Any] = None
    created_at: dt.datetime


# ---------- Grievance (Phase 13) ----------

class GrievanceCreate(BaseModel):
    transaction_id: Optional[int] = None
    against_user: Optional[str] = None
    against_user_id: Optional[int] = None
    category: str
    description: str
    evidence_urls: List[str] = []
    priority: str = "MEDIUM"


class GrievanceUpdate(BaseModel):
    status: Optional[str] = None
    resolution: Optional[str] = None
    priority: Optional[str] = None
    assigned_to: Optional[str] = None


class GrievanceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    transaction_id: Optional[int]
    raised_by: str
    raised_by_id: int
    against_user: Optional[str]
    against_user_id: Optional[int]
    category: str
    description: str
    evidence_urls: List[str]
    status: str
    priority: str
    assigned_to: Optional[str]
    resolution: Optional[str]
    created_at: dt.datetime
    updated_at: dt.datetime
    resolved_at: Optional[dt.datetime]


# ---------- Rating (Phase 14) ----------

class RatingCreate(BaseModel):
    transaction_id: int
    rating: float
    review: Optional[str] = None


class RatingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    transaction_id: int
    rater_role: str
    rater_id: int
    ratee_role: str
    ratee_id: int
    rating: float
    review: Optional[str]
    created_at: dt.datetime
