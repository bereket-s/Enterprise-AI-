from datetime import date as date_type

from sqlalchemy import Date, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TenantMixin


class UsageMetric(Base, TenantMixin):
    """Per-tenant, per-day request counters — the "usage metrics for billing"
    observability gap from docs/architecture.md §10. Incremented by
    app/core/middleware.py on every authenticated request; a real billing system
    would read this table rather than re-deriving usage from raw logs."""

    __tablename__ = "usage_metrics"
    __table_args__ = (UniqueConstraint("organization_id", "module_key", "day"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    module_key: Mapped[str] = mapped_column(String(50), index=True)
    day: Mapped[date_type] = mapped_column(Date, index=True)
    request_count: Mapped[int] = mapped_column(Integer, default=0)
