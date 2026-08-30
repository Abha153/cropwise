from fastapi import APIRouter

from app import schemas
from app.mock_data.locations import MARKETS, nearest_markets
from app.services.transport_optimizer import shared_transport_plan

router = APIRouter(prefix="/logistics", tags=["logistics"])

VEHICLES = [
    {"vehicle": "Mahindra Bolero Pickup", "capacity_kg": 1500, "cost_per_km": 14, "type": "mini-truck"},
    {"vehicle": "Tata Ace (Chhota Hathi)", "capacity_kg": 750, "cost_per_km": 9, "type": "mini-truck"},
    {"vehicle": "Eicher 14ft Truck", "capacity_kg": 5000, "cost_per_km": 22, "type": "truck"},
    {"vehicle": "Tata 407 Truck", "capacity_kg": 2500, "cost_per_km": 17, "type": "truck"},
]


@router.get("/vehicles")
def get_vehicles():
    return VEHICLES


@router.post("/farmpool")
def farmpool(payload: schemas.FarmPoolRequest):
    if payload.destination_market:
        destination = payload.destination_market
    else:
        candidates = [m for m in nearest_markets(payload.location) if m["name"] != payload.location]
        destination = candidates[0]["name"] if candidates else MARKETS[0]["name"]

    plan = shared_transport_plan(
        crop=payload.crop, location=payload.location,
        quantity_kg=payload.quantity_kg, destination_market=destination,
    )
    return plan
