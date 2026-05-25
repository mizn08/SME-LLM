from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class SMEProfile(Base):
    __tablename__ = "sme_profile"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    business_name: Mapped[str] = mapped_column(String(255), nullable=False)
    industry: Mapped[str] = mapped_column(String(128), nullable=False)
    bumiputera_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    veteran_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    annual_revenue_rm: Mapped[float] = mapped_column(Float, default=0.0)
    employee_count: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    transactions = relationship("FinancialTransaction", back_populates="sme")
    snapshots = relationship("CashFlowSnapshot", back_populates="sme")
    predictions = relationship("PredictionLog", back_populates="sme")
