from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TenantMixin, utcnow


class ModelVersion(Base, TenantMixin):
    """One row per trained model artefact, per org, per module — the "model
    registry with versioning" from docs/architecture.md §10. Training a module
    (manually or via a scheduled retrain, app/core/scheduler.py) always adds a new
    version rather than overwriting the previous one; exactly one version per
    (organization, module) is `is_active` at a time, which is the one the module's
    scoring endpoints load."""

    __tablename__ = "model_versions"

    id: Mapped[int] = mapped_column(primary_key=True)
    module_key: Mapped[str] = mapped_column(String(50), index=True)
    version: Mapped[int] = mapped_column(Integer)
    artifact_path: Mapped[str] = mapped_column(String(500))
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    feature_columns: Mapped[list] = mapped_column(JSON, default=list)
    training_reference_stats: Mapped[dict] = mapped_column(JSON, default=dict)  # per-feature mean/std, for drift checks
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    trigger: Mapped[str] = mapped_column(String(20), default="manual")  # manual | scheduled
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
