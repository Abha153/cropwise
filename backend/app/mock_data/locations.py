"""
Mock market/location data. Coordinates are approximate real-world values for
towns in Chhattisgarh, India, so distance and transport-cost math behaves
realistically in the demo. In production this would be replaced by a live
mandi/APMC directory API.
"""
import math

MARKETS = [
    {"name": "Bilaspur",     "latitude": 22.0797, "longitude": 82.1409, "state": "Chhattisgarh"},
    {"name": "Raipur",       "latitude": 21.2514, "longitude": 81.6296, "state": "Chhattisgarh"},
    {"name": "Durg",         "latitude": 21.1904, "longitude": 81.2849, "state": "Chhattisgarh"},
    {"name": "Raigarh",      "latitude": 21.8974, "longitude": 83.3950, "state": "Chhattisgarh"},
    {"name": "Korba",        "latitude": 22.3595, "longitude": 82.7501, "state": "Chhattisgarh"},
    {"name": "Bilha",        "latitude": 22.1500, "longitude": 82.0500, "state": "Chhattisgarh"},
    {"name": "Ambikapur",    "latitude": 23.1200, "longitude": 83.1950, "state": "Chhattisgarh"},
    {"name": "Rajnandgaon",  "latitude": 21.0972, "longitude": 81.0388, "state": "Chhattisgarh"},
    {"name": "Mahasamund",   "latitude": 21.1093, "longitude": 82.0980, "state": "Chhattisgarh"},
    {"name": "Jagdalpur",    "latitude": 19.0748, "longitude": 82.0198, "state": "Chhattisgarh"},
]

MARKET_BY_NAME = {m["name"]: m for m in MARKETS}


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    """Great-circle distance between two points, in kilometres."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def distance_between(market_a: str, market_b: str) -> float:
    a = MARKET_BY_NAME.get(market_a)
    b = MARKET_BY_NAME.get(market_b)
    if not a or not b:
        return 50.0  # fallback default
    if a["name"] == b["name"]:
        return 4.0  # local/intra-town movement
    return round(haversine_km(a["latitude"], a["longitude"], b["latitude"], b["longitude"]), 1)


def nearest_markets(location: str, limit: int = None):
    """Return all markets sorted by distance from `location` (nearest first)."""
    ranked = sorted(MARKETS, key=lambda m: distance_between(location, m["name"]))
    if limit:
        ranked = ranked[:limit]
    return ranked
