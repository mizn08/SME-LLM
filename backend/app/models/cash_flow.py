from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class CashFlowSnapshot(Base):
    __tablename__ = "cash_flow_snapshot"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    sme_id: Mapped[int] = mapped_column(ForeignKey("sme_profile.id"), nullable=False, index=True)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    current_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    days_cash_on_hand: Mapped[float] = mapped_column(Float, nullable=False)
    burn_rate_monthly_rm: Mapped[float] = mapped_column(Float, nullable=False)
    revenue_mtd_rm: Mapped[float] = mapped_column(Float, default=0.0)
    expense_mtd_rm: Mapped[float] = mapped_column(Float, default=0.0)
    net_operating_cash_rm: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    sme = relationship("SMEProfile", back_populates="snapshots")
