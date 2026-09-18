"""Model registry: every training run adds a new versioned artefact rather than
silently overwriting the last one, and exactly one version per (org, module) is
marked active. Closes the "model registry with versioning" gap in
docs/architecture.md §10 without changing how any module's train_and_score()
computes its metrics — this only wraps the persistence step.
"""
from __future__ import annotations

from pathlib import Path

import joblib
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.model_registry import ModelVersion

ARTIFACT_ROOT = get_settings().data_raw_dir.parent.parent / "backend" / "app" / "ml" / "artifacts" / "registry"


def save_version(
    db: Session,
    org_id: int,
    module_key: str,
    model,
    metrics: dict,
    feature_columns: list[str] | None = None,
    reference_stats: dict | None = None,
    trigger: str = "manual",
) -> ModelVersion:
    prev_max = (
        db.query(ModelVersion)
        .filter(ModelVersion.organization_id == org_id, ModelVersion.module_key == module_key)
        .order_by(ModelVersion.version.desc())
        .first()
    )
    next_version = (prev_max.version + 1) if prev_max else 1

    # deactivate any previously-active version for this org/module
    db.query(ModelVersion).filter(
        ModelVersion.organization_id == org_id, ModelVersion.module_key == module_key, ModelVersion.is_active.is_(True)
    ).update({"is_active": False})

    org_dir = ARTIFACT_ROOT / module_key / f"org{org_id}"
    org_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = org_dir / f"v{next_version}.joblib"
    joblib.dump(model, artifact_path)

    version = ModelVersion(
        organization_id=org_id,
        module_key=module_key,
        version=next_version,
        artifact_path=str(artifact_path),
        metrics=metrics,
        feature_columns=feature_columns or [],
        training_reference_stats=reference_stats or {},
        is_active=True,
        trigger=trigger,
    )
    db.add(version)
    db.commit()
    db.refresh(version)
    return version


def get_active_version(db: Session, org_id: int, module_key: str) -> ModelVersion | None:
    return (
        db.query(ModelVersion)
        .filter(ModelVersion.organization_id == org_id, ModelVersion.module_key == module_key, ModelVersion.is_active.is_(True))
        .first()
    )


def load_active_model(db: Session, org_id: int, module_key: str):
    version = get_active_version(db, org_id, module_key)
    if version is None:
        return None
    return joblib.load(version.artifact_path)


def list_versions(db: Session, org_id: int, module_key: str) -> list[ModelVersion]:
    return (
        db.query(ModelVersion)
        .filter(ModelVersion.organization_id == org_id, ModelVersion.module_key == module_key)
        .order_by(ModelVersion.version.desc())
        .all()
    )


def activate_version(db: Session, org_id: int, module_key: str, version_number: int) -> ModelVersion:
    target = (
        db.query(ModelVersion)
        .filter(ModelVersion.organization_id == org_id, ModelVersion.module_key == module_key, ModelVersion.version == version_number)
        .first()
    )
    if target is None:
        raise ValueError(f"No version {version_number} found for module '{module_key}'")
    db.query(ModelVersion).filter(
        ModelVersion.organization_id == org_id, ModelVersion.module_key == module_key, ModelVersion.is_active.is_(True)
    ).update({"is_active": False})
    target.is_active = True
    db.commit()
    db.refresh(target)
    return target
