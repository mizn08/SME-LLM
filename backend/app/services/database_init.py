"""Create schema and seed reference + transaction data (shared by API lifespan and init_db.py)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from sqlalchemy import inspect, text

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import engine
import app.models  # noqa: F401 — register all tables for create_all (incl. application_tracker)
from app.models.sme import SMEProfile
from app.services.bandit_service import _ensure_arms
from app.services.seed_data import seed_reference_data
from app.services.seed_goals import seed_demo_goals
from app.services.seed_transactions import seed_six_month_transactions


def _ensure_quote_columns() -> None:
    """SQLite dev DBs created before quote_log columns were added."""
    insp = inspect(engine)
    if "quote_log" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("quote_log")}
    alters = []
    if "budget_rm" not in cols:
        alters.append("ALTER TABLE quote_log ADD COLUMN budget_rm FLOAT")
    if "agent_duration_sec" not in cols:
        alters.append("ALTER TABLE quote_log ADD COLUMN agent_duration_sec FLOAT")
    if not alters:
        return
    with engine.begin() as conn:
        for stmt in alters:
            try:
                conn.execute(text(stmt))
            except Exception:
                pass


def init_database(db: Session, *, create_schema: bool = True) -> dict[str, int | str]:
    if create_schema:
        Base.metadata.create_all(bind=engine)
        if get_settings().is_sqlite:
            _ensure_quote_columns()

    before = db.query(SMEProfile).count()
    seed_reference_data(db)
    after = db.query(SMEProfile).count()
    txn_count = seed_six_month_transactions(db)
    _ensure_arms(db)
    goals_seeded = seed_demo_goals(db)

    return {
        "status": "ok",
        "sme_profiles": after,
        "reference_seeded": after - before if before == 0 else "already_present",
        "transactions_inserted": txn_count,
        "goals_seeded": goals_seeded,
    }
