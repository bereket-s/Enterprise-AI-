from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TenantMixin, utcnow


class AuditLog(Base, TenantMixin):
    """Records every sensitive administrative action — module toggles, KPI-weight
    edits, integration credential changes, API-key creation/revocation — so a real
    deployment has a trail of who changed what and when, independent of the
    Copilot's own ChatLog audit trail."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(100))
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
