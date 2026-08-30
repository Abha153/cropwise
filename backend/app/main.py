from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine, run_lightweight_migrations
from app.seed_data import seed
from app.routers import (
    auth, farmers, buyers, listings, offers, market, advisor,
    forecast, matching, logistics, profit, group_selling, notifications,
    quality, assistant, admin,
)
from app.routers import lots, buyer_demands, buyer_verification
from app.routers import transactions, payments, grievances
from app.routers import storage, transport, ratings

Base.metadata.create_all(bind=engine)
run_lightweight_migrations()

app = FastAPI(
    title=settings.app_name,
    description="CropWise API -- Smart Markets. Better Prices. Stronger Farmers.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    seed()


@app.get("/")
def root():
    return {
        "name": "CropWise API",
        "tagline": "Smart Markets. Better Prices. Stronger Farmers.",
        "status": "ok",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(farmers.router)
app.include_router(buyers.router)
app.include_router(listings.router)
app.include_router(offers.router)
app.include_router(market.router)
app.include_router(advisor.router)
app.include_router(forecast.router)
app.include_router(matching.router)
app.include_router(logistics.router)
app.include_router(profit.router)
app.include_router(group_selling.router)
app.include_router(notifications.router)
app.include_router(quality.router)
app.include_router(assistant.router)
app.include_router(admin.router)
app.include_router(lots.router)
app.include_router(buyer_demands.router)
app.include_router(buyer_verification.router)
app.include_router(transactions.router)
app.include_router(payments.router)
app.include_router(grievances.router)
app.include_router(storage.router)
app.include_router(transport.router)
app.include_router(ratings.router)
