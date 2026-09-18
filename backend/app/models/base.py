from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)


class TenantMixin:
    """Every tenant-scoped table carries an organization_id.

    All queries against tenant-scoped tables MUST filter by organization_id
    (see app.core.deps.tenant_scoped_query) so that one company can never see
    another company's rows.
    """

    organization_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("organizations.id"), nullable=False, index=True
    )
