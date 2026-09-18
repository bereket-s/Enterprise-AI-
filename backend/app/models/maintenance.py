from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TenantMixin, utcnow


class Equipment(Base, TenantMixin):
    __tablename__ = "equipment"

    id: Mapped[int] = mapped_column(primary_key=True)
    external_ref: Mapped[str] = mapped_column(String(50), index=True)
    machine_type: Mapped[str] = mapped_column(String(10), default="M")  # L/M/H per AI4I dataset

    # Nullable so "bring your own data" companies can populate only the sensors
    # they actually have; the AI4I seed data (backend/scripts/seed_demo_org.py)
    # always provides all five. Anything beyond these five (e.g. "pressure",
    # which the AI4I dataset doesn't have) is stored in extra_readings instead of
    # requiring a schema change per company's sensor naming.
    air_temp_k: Mapped[float | None] = mapped_column(Float, nullable=True)
    process_temp_k: Mapped[float | None] = mapped_column(Float, nullable=True)
    rotational_speed_rpm: Mapped[float | None] = mapped_column(Float, nullable=True)
    torque_nm: Mapped[float | None] = mapped_column(Float, nullable=True)
    tool_wear_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    extra_readings: Mapped[dict] = mapped_column(JSON, default=dict)

    actual_failure: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    failure_risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    risk_label: Mapped[str] = mapped_column(String(20), default="low")
    contributing_factors: Mapped[list] = mapped_column(JSON, default=list)

    predicted_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
