from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TenantMixin, utcnow


class FraudTransaction(Base, TenantMixin):
    __tablename__ = "fraud_transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    external_ref: Mapped[str] = mapped_column(String(50), index=True)
    amount: Mapped[float] = mapped_column(Float)
    occurred_at: Mapped[datetime] = mapped_column(DateTime)
    features: Mapped[dict] = mapped_column(JSON)  # raw model features (V1..V28, Time, Amount)

    actual_is_fraud: Mapped[bool | None] = mapped_column(Boolean, nullable=True)  # ground truth, if known
    risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    risk_label: Mapped[str] = mapped_column(String(20), default="low")  # low | medium | high | critical
    reason_codes: Mapped[list] = mapped_column(JSON, default=list)

    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending|investigating|approved|blocked
    scored_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
