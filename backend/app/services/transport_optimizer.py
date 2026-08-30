"""
Transport & logistics cost modelling.

Rates are realistic approximations for small/medium truck hire in rural
India (2025-26 range), used consistently across the app so every feature
(market comparison, advisor, profit calculator, FarmPool) agrees with each
other.
"""
import hashlib
import random

from app.mock_data.locations import distance_between

PER_KM_PER_TON_RATE = 7.5      # INR per km per tonne
LOCAL_BASE_FEE = 60.0          # INR, very short local haul
LONG_HAUL_BASE_FEE = 150.0     # INR, loading/booking fee for a normal trip
BIG_TRUCK_BASE_FEE = 320.0     # INR, larger shared vehicle booking fee
SHARED_RATE_DISCOUNT = 0.80    # bulk full-truckload gets a per-tonne discount
MANDI_CHARGE_RATE = 0.015      # ~1.5% market/commission fee on transaction value
HANDLING_COST_PER_KG = 0.15    # loading/unloading/labour


def estimate_transport_cost(distance_km: float, quantity_kg: float) -> float:
    tonnes = max(quantity_kg / 1000.0, 0.05)
    base_fee = LOCAL_BASE_FEE if distance_km <= 5 else LONG_HAUL_BASE_FEE
    cost = base_fee + PER_KM_PER_TON_RATE * distance_km * tonnes
    return round(cost, 2)


def estimate_mandi_charges(quantity_kg: float, price_per_kg: float) -> float:
    value = quantity_kg * price_per_kg
    return round(value * MANDI_CHARGE_RATE, 2)


def estimate_handling_cost(quantity_kg: float) -> float:
    return round(quantity_kg * HANDLING_COST_PER_KG, 2)


def net_profit_breakdown(quantity_kg: float, price_per_kg: float, distance_km: float) -> dict:
    gross = round(quantity_kg * price_per_kg, 2)
    transport = estimate_transport_cost(distance_km, quantity_kg)
    mandi = estimate_mandi_charges(quantity_kg, price_per_kg)
    handling = estimate_handling_cost(quantity_kg)
    net = round(gross - transport - mandi - handling, 2)
    return {
        "gross_revenue": gross,
        "transport_cost": transport,
        "mandi_charges": mandi,
        "handling_cost": handling,
        "net_profit": net,
    }


def _seed_int(*parts) -> int:
    digest = hashlib.sha256("::".join(str(p) for p in parts).encode()).hexdigest()
    return int(digest[:8], 16)


def find_nearby_pool_partners(crop: str, location: str, quantity_kg: float):
    """
    Simulate other nearby farmers with the same crop available for shared
    transport (FarmPool). Deterministic per crop+location so the demo is
    stable across refreshes.
    """
    rng = random.Random(_seed_int("farmpool", crop, location))
    count = rng.randint(2, 4)
    partners = []
    names = ["Anita Patel", "Deepak Yadav", "Kavita Sahu", "Vikram Netam", "Farida Khan", "Prakash Rao"]
    rng.shuffle(names)
    for i in range(count):
        partners.append({
            "farmer_name": names[i % len(names)],
            "distance_from_you_km": round(rng.uniform(2, 14), 1),
            "quantity_kg": round(rng.uniform(300, 1200), 0),
        })
    return partners


def shared_transport_plan(crop: str, location: str, quantity_kg: float, destination_market: str):
    distance = distance_between(location, destination_market)
    partners = find_nearby_pool_partners(crop, location, quantity_kg)

    my_individual_cost = estimate_transport_cost(distance, quantity_kg)

    total_pool_quantity = quantity_kg + sum(p["quantity_kg"] for p in partners)
    tonnes = total_pool_quantity / 1000.0
    shared_total_cost = BIG_TRUCK_BASE_FEE + PER_KM_PER_TON_RATE * SHARED_RATE_DISCOUNT * distance * tonnes
    my_share = shared_total_cost * (quantity_kg / total_pool_quantity)
    my_share = round(my_share, 2)
    savings = round(my_individual_cost - my_share, 2)

    return {
        "destination_market": destination_market,
        "distance_km": distance,
        "your_quantity_kg": quantity_kg,
        "pool_partners": partners,
        "total_pool_quantity_kg": round(total_pool_quantity, 1),
        "your_individual_transport_cost": my_individual_cost,
        "your_shared_transport_cost": my_share,
        "estimated_savings": max(savings, 0),
        "savings_pct": round((savings / my_individual_cost) * 100, 1) if my_individual_cost else 0,
    }
