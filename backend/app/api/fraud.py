from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api import _ingest_helpers
from app.core.database import get_db
from app.core.deps import require_module_enabled
from app.models.evaluation import ModelEvaluation
from app.models.fraud import FraudTransaction
from app.schemas.bi import IngestPreview
from app.schemas.fraud import EvaluationOut, FraudTransactionOut, StatusUpdateRequest
from app.schemas.integrations import GenericIngestResult
from app.services import fraud_service

router = APIRouter(
    prefix="/api/fraud",
    tags=["fraud"],
    dependencies=[Depends(require_module_enabled("fraud"))],
)

VALID_STATUSES = {"pending", "investigating", "approved", "blocked"}


@router.post("/ingest/preview", response_model=IngestPreview)
def preview_ingest(file: UploadFile):
    return _ingest_helpers.preview("fraud", file)


@router.post("/ingest/commit", response_model=GenericIngestResult)
def commit_ingest(
    file: UploadFile,
    mapping: str = Form(...),
    org_id: int = Depends(require_module_enabled("fraud")),
    db: Session = Depends(get_db),
):
    result = _ingest_helpers.commit("fraud", db, org_id, file, mapping)
    return GenericIngestResult(records_ingested=result.get("transactions_ingested", 0))


@router.post("/train", response_model=EvaluationOut)
def train_model(org_id: int = Depends(require_module_enabled("fraud")), db: Session = Depends(get_db)):
    try:
        return fraud_service.train_and_score(db, org_id)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc


@router.get("/evaluation/latest", response_model=EvaluationOut)
def latest_evaluation(org_id: int = Depends(require_module_enabled("fraud")), db: Session = Depends(get_db)):
    row = (
        db.query(ModelEvaluation)
        .filter(ModelEvaluation.organization_id == org_id, ModelEvaluation.module_key == "fraud")
        .order_by(ModelEvaluation.generated_at.desc())
        .first()
    )
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No fraud model has been trained yet")
    return row


@router.get("/transactions", response_model=list[FraudTransactionOut])
def list_transactions(
    risk_label: str | None = None,
    limit: int = 100,
    org_id: int = Depends(require_module_enabled("fraud")),
    db: Session = Depends(get_db),
):
    query = db.query(FraudTransaction).filter(FraudTransaction.organization_id == org_id)
    if risk_label:
        query = query.filter(FraudTransaction.risk_label == risk_label)
    return query.order_by(FraudTransaction.risk_score.desc()).limit(limit).all()


@router.put("/transactions/{transaction_id}/status", response_model=FraudTransactionOut)
def update_status(
    transaction_id: int,
    payload: StatusUpdateRequest,
    org_id: int = Depends(require_module_enabled("fraud")),
    db: Session = Depends(get_db),
):
    if payload.status not in VALID_STATUSES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"status must be one of {sorted(VALID_STATUSES)}")
    txn = (
        db.query(FraudTransaction)
        .filter(FraudTransaction.id == transaction_id, FraudTransaction.organization_id == org_id)
        .first()
    )
    if txn is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Transaction not found")
    txn.status = payload.status
    db.commit()
    db.refresh(txn)
    return txn
