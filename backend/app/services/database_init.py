"""Create schema and seed reference + transaction data (shared by API lifespan and init_db.py)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.session import engine
import app.models  # noqa: F401 — register all tables for create_all (incl. application_tracker)
from app.models.sme import SMEProfile
from app.services.bandit_service import _ensure_arms
from app.services.seed_data import seed_reference_data
from app.services.seed_transactions import seed_six_month_transactions


def init_database(db: Session, *, create_schema: bool = True) -> dict[str, int | str]:
    if create_schema:
        Base.metadata.create_all(bind=engine)

    before = db.query(SMEProfile).count()
    seed_reference_data(db)
    after = db.query(SMEProfile).count()
    txn_count = seed_six_month_transactions(db)
    _ensure_arms(db)

    return {
        "status": "ok",
        "sme_profiles": after,
        "reference_seeded": after - before if before == 0 else "already_present",
        "transactions_inserted": txn_count,
    }
