from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api import _ingest_helpers
from app.core.database import get_db
from app.core.deps import require_module_enabled
from app.models.evaluation import ModelEvaluation
from app.models.maintenance import Equipment
from app.schemas.bi import IngestPreview
from app.schemas.fraud import EvaluationOut
from app.schemas.integrations import GenericIngestResult
from app.schemas.maintenance import EquipmentOut
from app.services import maintenance_service

router = APIRouter(
    prefix="/api/maintenance",
    tags=["maintenance"],
    dependencies=[Depends(require_module_enabled("maintenance"))],
)


@router.post("/ingest/preview", response_model=IngestPreview)
def preview_ingest(file: UploadFile):
    return _ingest_helpers.preview("maintenance", file)


@router.post("/ingest/commit", response_model=GenericIngestResult)
def commit_ingest(
    file: UploadFile,
    mapping: str = Form(...),
    org_id: int = Depends(require_module_enabled("maintenance")),
    db: Session = Depends(get_db),
):
    result = _ingest_helpers.commit("maintenance", db, org_id, file, mapping)
    return GenericIngestResult(records_ingested=result.get("equipment_ingested", 0))


@router.post("/train", response_model=EvaluationOut)
def train_model(org_id: int = Depends(require_module_enabled("maintenance")), db: Session = Depends(get_db)):
    try:
        return maintenance_service.train_and_score(db, org_id)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc


@router.get("/evaluation/latest", response_model=EvaluationOut)
def latest_evaluation(org_id: int = Depends(require_module_enabled("maintenance")), db: Session = Depends(get_db)):
    row = (
        db.query(ModelEvaluation)
        .filter(ModelEvaluation.organization_id == org_id, ModelEvaluation.module_key == "maintenance")
        .order_by(ModelEvaluation.generated_at.desc())
        .first()
    )
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No maintenance model has been trained yet")
    return row


@router.get("/equipment", response_model=list[EquipmentOut])
def list_equipment(
    risk_label: str | None = None,
    limit: int = 100,
    org_id: int = Depends(require_module_enabled("maintenance")),
    db: Session = Depends(get_db),
):
    query = db.query(Equipment).filter(Equipment.organization_id == org_id)
    if risk_label:
        query = query.filter(Equipment.risk_label == risk_label)
    return query.order_by(Equipment.failure_risk_score.desc()).limit(limit).all()
