from datetime import datetime

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TenantMixin, utcnow


class ModelEvaluation(Base, TenantMixin):
    """One row per training run, across every module — the single source for Chapter 4's tables."""

    __tablename__ = "model_evaluations"

    id: Mapped[int] = mapped_column(primary_key=True)
    module_key: Mapped[str] = mapped_column(String(50), index=True)
    model_name: Mapped[str] = mapped_column(String(100))
    metrics: Mapped[dict] = mapped_column(JSON)  # e.g. {"precision":..,"recall":..,"f1":..,"roc_auc":..}
    train_rows: Mapped[int] = mapped_column(default=0)
    test_rows: Mapped[int] = mapped_column(default=0)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
