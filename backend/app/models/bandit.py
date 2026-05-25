from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class BanditArmStat(Base):
    __tablename__ = "bandit_arm_stat"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    arm: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    pulls: Mapped[int] = mapped_column(Integer, default=0)
    total_reward: Mapped[float] = mapped_column(Float, default=0.0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
    )


class BanditFeedback(Base):
    __tablename__ = "bandit_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sme_id: Mapped[int] = mapped_column(ForeignKey("sme_profile.id"), index=True)
    prediction_id: Mapped[int | None] = mapped_column(ForeignKey("prediction_log.id"), nullable=True)
    arm: Mapped[str] = mapped_column(String(32), nullable=False)
    reward: Mapped[float] = mapped_column(Float, default=0.0)
    accepted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
