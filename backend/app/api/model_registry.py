from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.audit import log_action
from app.core.database import get_db
from app.core.deps import current_org_id, require_roles
from app.ml import model_registry
from app.models.user import RoleEnum, User
from app.schemas.model_registry import DriftReportOut, ModelVersionOut

router = APIRouter(prefix="/api/models", tags=["model-registry"])

_DRIFT_FUNCS = {}


def _drift_func(module_key: str):
    if not _DRIFT_FUNCS:
        from app.services import fraud_service, maintenance_service, workforce_service

        _DRIFT_FUNCS.update(
            {"fraud": fraud_service.drift_report, "maintenance": maintenance_service.drift_report, "workforce": workforce_service.drift_report}
        )
    return _DRIFT_FUNCS.get(module_key)


@router.get("/{module_key}", response_model=list[ModelVersionOut])
def list_model_versions(module_key: str, org_id: int = Depends(current_org_id), db: Session = Depends(get_db)):
    return model_registry.list_versions(db, org_id, module_key)


@router.post("/{module_key}/{version}/activate", response_model=ModelVersionOut)
def activate_model_version(
    module_key: str,
    version: int,
    org_id: int = Depends(current_org_id),
    user: User = Depends(require_roles(RoleEnum.org_admin, RoleEnum.super_admin)),
    db: Session = Depends(get_db),
):
    try:
        activated = model_registry.activate_version(db, org_id, module_key, version)
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    log_action(db, org_id, user.id, "model_version.activated", {"module_key": module_key, "version": version})
    return activated


@router.get("/{module_key}/drift", response_model=DriftReportOut)
def get_drift_report(module_key: str, org_id: int = Depends(current_org_id), db: Session = Depends(get_db)):
    func = _drift_func(module_key)
    if func is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"No drift monitoring available for module '{module_key}'")
    return func(db, org_id)
