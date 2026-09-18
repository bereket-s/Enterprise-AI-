from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ModelVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())
    id: int
    version: int
    metrics: dict
    feature_columns: list
    is_active: bool
    trigger: str
    created_at: datetime


class DriftReportOut(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    drift_checked: bool
    reason: str | None = None
    drifted_features: dict | None = None
    model_version: int | None = None
