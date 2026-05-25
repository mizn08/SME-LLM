"""Application Tracker — persists SME financing application status."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ApplicationTracker(Base):
    __tablename__ = "application_tracker"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    sme_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    product_type: Mapped[str] = mapped_column(String(64), nullable=False)   # bnpl | micro_credit | grant
    status: Mapped[str] = mapped_column(String(64), default="draft")        # draft|submitted|under_review|approved|rejected
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)
