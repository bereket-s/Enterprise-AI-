from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, utcnow


class Organization(Base, TimestampMixin):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    industry: Mapped[str] = mapped_column(String(100), default="general")
    size: Mapped[str] = mapped_column(String(50), default="unknown")
    country: Mapped[str] = mapped_column(String(100), default="unknown")

    users: Mapped[list["User"]] = relationship(back_populates="organization")
    module_enablements: Mapped[list["ModuleEnablement"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )


class ModuleEnablement(Base):
    __tablename__ = "module_enablements"
    __table_args__ = (UniqueConstraint("organization_id", "module_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    module_key: Mapped[str] = mapped_column(String(50), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    organization: Mapped["Organization"] = relationship(back_populates="module_enablements")
