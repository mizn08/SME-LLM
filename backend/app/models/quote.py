from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class QuoteLog(Base):
    __tablename__ = "quote_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    sme_id: Mapped[int] = mapped_column(ForeignKey("sme_profile.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), default="Sales quote")
    location: Mapped[str] = mapped_column(String(128), default="Kuala Lumpur")
    line_items: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    subtotal_rm: Mapped[float] = mapped_column(Float, default=0.0)
    shipping_rm: Mapped[float] = mapped_column(Float, default=0.0)
    tax_rm: Mapped[float] = mapped_column(Float, default=0.0)
    discount_rm: Mapped[float] = mapped_column(Float, default=0.0)
    grand_total_rm: Mapped[float] = mapped_column(Float, default=0.0)
    tax_rate: Mapped[float] = mapped_column(Float, default=0.1)
    estimated_delivery_days: Mapped[int] = mapped_column(Integer, default=3)
    reasoning_summary: Mapped[str] = mapped_column(Text, default="")
    budget_rm: Mapped[float | None] = mapped_column(Float, nullable=True)
    agent_duration_sec: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
