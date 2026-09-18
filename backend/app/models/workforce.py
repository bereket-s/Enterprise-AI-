from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TenantMixin, utcnow


class Employee(Base, TenantMixin):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True)
    external_ref: Mapped[str] = mapped_column(String(50), index=True)
    full_name: Mapped[str] = mapped_column(String(200))
    department: Mapped[str] = mapped_column(String(100), index=True)
    job_role: Mapped[str] = mapped_column(String(100), default="")

    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    monthly_income: Mapped[float | None] = mapped_column(Float, nullable=True)
    years_at_company: Mapped[float | None] = mapped_column(Float, nullable=True)
    job_satisfaction: Mapped[float | None] = mapped_column(Float, nullable=True)  # 1-4 scale (source data)
    environment_satisfaction: Mapped[float | None] = mapped_column(Float, nullable=True)
    job_involvement: Mapped[float | None] = mapped_column(Float, nullable=True)  # 1-4 scale
    years_since_last_promotion: Mapped[float | None] = mapped_column(Float, nullable=True)
    performance_rating_actual: Mapped[float | None] = mapped_column(Float, nullable=True)  # ground truth

    attrition_actual: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    attrition_risk_score: Mapped[float] = mapped_column(Float, default=0.0)

    scores: Mapped[list["PerformanceScore"]] = relationship(back_populates="employee")
    goals: Mapped[list["Goal"]] = relationship(back_populates="employee")


class KPIWeightConfig(Base, TenantMixin):
    """Per-department, per-KPI weight — this is what makes scoring configurable instead of universal."""

    __tablename__ = "kpi_weight_configs"
    __table_args__ = (UniqueConstraint("organization_id", "department", "kpi_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    department: Mapped[str] = mapped_column(String(100), index=True)
    kpi_name: Mapped[str] = mapped_column(String(100))
    weight: Mapped[float] = mapped_column(Float)  # 0..1, weights per department should sum to ~1


class PerformanceScore(Base, TenantMixin):
    __tablename__ = "performance_scores"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    score: Mapped[float] = mapped_column(Float)
    breakdown: Mapped[dict] = mapped_column(JSON)  # {kpi_name: {value, weight, contribution}}
    main_improvement_area: Mapped[str | None] = mapped_column(String(100), nullable=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    employee: Mapped["Employee"] = relationship(back_populates="scores")


class Goal(Base, TenantMixin):
    __tablename__ = "goals"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    period: Mapped[str] = mapped_column(String(20), default="Q1")
    target_value: Mapped[float] = mapped_column(Float)
    current_value: Mapped[float] = mapped_column(Float, default=0.0)

    employee: Mapped["Employee"] = relationship(back_populates="goals")

    @property
    def progress_pct(self) -> float:
        if self.target_value == 0:
            return 0.0
        return round(100 * self.current_value / self.target_value, 1)
