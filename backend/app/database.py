from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def run_lightweight_migrations():
    """
    Additive-only migrations for existing tables. Safe to run on every
    startup -- no-op once columns already exist, never deletes rows.
    """
    if not settings.database_url.startswith("sqlite"):
        return
    with engine.connect() as conn:
        from sqlalchemy import text

        def add_column_if_missing(table: str, column: str, ddl_type: str):
            rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
            if not rows:
                return  # table doesn't exist yet -- create_all will handle it
            cols = [row[1] for row in rows]
            if column not in cols:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl_type}"))
                conn.commit()

        # Legacy columns
        add_column_if_missing("market_prices", "data_source", "VARCHAR NOT NULL DEFAULT 'demo'")
        add_column_if_missing("farmers", "last_login", "DATETIME")
        add_column_if_missing("buyers", "last_login", "DATETIME")

        # Phase 10: Transaction lifecycle columns
        add_column_if_missing("transactions", "lot_id", "INTEGER")
        add_column_if_missing("transactions", "offer_id", "INTEGER")
        add_column_if_missing("transactions", "updated_at", "DATETIME")

        # Phase 16: buyer notifications
        add_column_if_missing("notifications", "buyer_id", "INTEGER")

        # Integration pass: link transport requests to the transaction they
        # fulfil, so transport status can drive transaction status instead
        # of the transport module being an isolated island.
        add_column_if_missing("transport_requests", "transaction_id", "INTEGER")

        # Integration pass: let a buyer offer be made directly on a Lot
        # (Phase 4 sellable unit) instead of only the legacy CropListing,
        # and optionally record which BuyerDemand it fulfils -- this is
        # what actually connects Buyer Demand -> Lot -> Match -> Offer.
        add_column_if_missing("buyer_offers", "lot_id", "INTEGER")
        add_column_if_missing("buyer_offers", "buyer_demand_id", "INTEGER")
