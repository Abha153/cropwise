"""
Seed accounts for demo mode. All demo accounts share the password
'demo1234' so judges/testers can log in instantly. Passwords are hashed at
seed time in seed_data.py -- nothing here is stored as-is in the database.
"""

DEMO_PASSWORD = "demo1234"

DEMO_FARMERS = [
    {
        "name": "Ramesh Kumar",
        "email": "ramesh@cropwise.demo",
        "phone": "+91 98765 43210",
        "location": "Bilaspur",
        "latitude": 22.0797, "longitude": 82.1409,
        "crops": ["Tomato", "Paddy (Rice)", "Soybean"],
        "preferred_language": "hi",
        "rating": 4.6,
        "fpo_group": "Bilaspur Kisan Producer Company",
    },
    {
        "name": "Sunita Verma",
        "email": "sunita@cropwise.demo",
        "phone": "+91 98111 22334",
        "location": "Raigarh",
        "latitude": 21.8974, "longitude": 83.3950,
        "crops": ["Onion", "Wheat", "Maize"],
        "preferred_language": "hi",
        "rating": 4.8,
        "fpo_group": None,
    },
    {
        "name": "Manoj Sahu",
        "email": "manoj@cropwise.demo",
        "phone": "+91 97654 11223",
        "location": "Durg",
        "latitude": 21.1904, "longitude": 81.2849,
        "crops": ["Maize", "Chana (Gram)", "Groundnut"],
        "preferred_language": "en",
        "rating": 4.3,
        "fpo_group": "Durg Farmer Collective",
    },
]

DEMO_BUYERS = [
    {
        "company_name": "FreshFoods Processing Pvt. Ltd.",
        "email": "freshfoods@cropwise.demo",
        "phone": "+91 90000 11111",
        "location": "Raipur",
        "latitude": 21.2514, "longitude": 81.6296,
        "buyer_type": "processor",
        "verification_status": "verified",
        "reliability_score": 92.0,
        "payment_history_score": 95.0,
        "crops_of_interest": ["Tomato", "Onion", "Potato"],
    },
    {
        "company_name": "GreenBasket Retail",
        "email": "greenbasket@cropwise.demo",
        "phone": "+91 90000 22222",
        "location": "Bilaspur",
        "latitude": 22.0797, "longitude": 82.1409,
        "buyer_type": "retailer",
        "verification_status": "verified",
        "reliability_score": 88.0,
        "payment_history_score": 90.0,
        "crops_of_interest": ["Tomato", "Potato", "Onion", "Maize"],
    },
    {
        "company_name": "AgriExport India",
        "email": "agriexport@cropwise.demo",
        "phone": "+91 90000 33333",
        "location": "Durg",
        "latitude": 21.1904, "longitude": 81.2849,
        "buyer_type": "exporter",
        "verification_status": "verified",
        "reliability_score": 81.0,
        "payment_history_score": 84.0,
        "crops_of_interest": ["Soybean", "Chana (Gram)", "Groundnut", "Paddy (Rice)"],
    },
    {
        "company_name": "Chhattisgarh Wholesale Traders",
        "email": "wholesale@cropwise.demo",
        "phone": "+91 90000 44444",
        "location": "Korba",
        "latitude": 22.3595, "longitude": 82.7501,
        "buyer_type": "wholesaler",
        "verification_status": "pending",
        "reliability_score": 68.0,
        "payment_history_score": 72.0,
        "crops_of_interest": ["Wheat", "Paddy (Rice)", "Maize"],
    },
]
