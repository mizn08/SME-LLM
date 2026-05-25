from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DeviceToken(Base):
    __tablename__ = "device_token"
    __table_args__ = (UniqueConstraint("sme_id", "token", name="uq_sme_token"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    sme_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    token: Mapped[str] = mapped_column(String(512), nullable=False)
    platform: Mapped[str] = mapped_column(String(32), default="fcm")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
