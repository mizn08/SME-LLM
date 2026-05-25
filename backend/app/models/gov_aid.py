from sqlalchemy import Boolean, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class GovFinancialAid(Base):
    __tablename__ = "gov_financial_aid"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    scheme_name: Mapped[str] = mapped_column(String(255), nullable=False)
    agency: Mapped[str] = mapped_column(String(128), nullable=False)
    aid_type: Mapped[str] = mapped_column(String(64), nullable=False)
    max_amount_rm: Mapped[float | None] = mapped_column(Float, nullable=True)
    interest_rate_label: Mapped[str | None] = mapped_column(String(128), nullable=True)
    tenure_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    approval_speed_label: Mapped[str | None] = mapped_column(String(128), nullable=True)
    requires_bumiputera: Mapped[bool] = mapped_column(Boolean, default=False)
    requires_veteran: Mapped[bool] = mapped_column(Boolean, default=False)
    industry_keywords: Mapped[str | None] = mapped_column(Text, nullable=True)
    digitalisation_only: Mapped[bool] = mapped_column(Boolean, default=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
