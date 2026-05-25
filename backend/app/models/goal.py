from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class FinancialGoal(Base):
    __tablename__ = "financial_goal"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    sme_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    target_amount_rm: Mapped[float] = mapped_column(Float, nullable=False)
    current_amount_rm: Mapped[float] = mapped_column(Float, default=0.0)
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    category: Mapped[str] = mapped_column(String(64), default="savings")
    status: Mapped[str] = mapped_column(String(32), default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
