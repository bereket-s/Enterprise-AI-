import io
import json

import pandas as pd
from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_module_enabled
from app.models.bi import ForecastResult
from app.services import bi_service
from app.services.data_mapping import suggest_mapping
from app.schemas.bi import ForecastOut, IngestPreview, IngestResult, KPISummary

router = APIRouter(
    prefix="/api/bi",
    tags=["business-intelligence"],
    dependencies=[Depends(require_module_enabled("bi_forecasting"))],
)


def _read_csv(file: UploadFile) -> pd.DataFrame:
    content = file.file.read()
    try:
        return pd.read_csv(io.BytesIO(content))
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Could not parse CSV: {exc}") from exc


@router.post("/ingest/preview", response_model=IngestPreview)
def preview_ingest(file: UploadFile):
    df = _read_csv(file)
    mapping = suggest_mapping(list(df.columns), bi_service.CANONICAL_FIELDS)
    return IngestPreview(
        columns=list(df.columns),
        suggested_mapping=mapping,
        sample_rows=df.head(5).fillna("").to_dict(orient="records"),
    )


@router.post("/ingest/commit", response_model=IngestResult)
def commit_ingest(
    file: UploadFile,
    mapping: str = Form(...),  # JSON string: {canonical_field: source_column}
    org_id: int = Depends(require_module_enabled("bi_forecasting")),
    db: Session = Depends(get_db),
):
    df = _read_csv(file)
    field_map = json.loads(mapping)
    missing_required = [f for f in ("product_id", "quantity", "unit_price", "transaction_date") if not field_map.get(f)]
    if missing_required:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Missing required mapping for: {missing_required}")

    renamed = df.rename(columns={v: k for k, v in field_map.items() if v})
    result = bi_service.ingest_sales_dataframe(db, org_id, renamed)
    return IngestResult(**result)


@router.get("/kpis", response_model=KPISummary)
def get_kpis(org_id: int = Depends(require_module_enabled("bi_forecasting")), db: Session = Depends(get_db)):
    return bi_service.compute_kpis(db, org_id)


@router.post("/forecast/run", response_model=ForecastOut)
def run_forecast(
    horizon_days: int = 14,
    org_id: int = Depends(require_module_enabled("bi_forecasting")),
    db: Session = Depends(get_db),
):
    try:
        return bi_service.run_company_forecast(db, org_id, horizon_days=horizon_days)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc


@router.get("/forecast/latest", response_model=ForecastOut)
def latest_forecast(org_id: int = Depends(require_module_enabled("bi_forecasting")), db: Session = Depends(get_db)):
    result = (
        db.query(ForecastResult)
        .filter(ForecastResult.organization_id == org_id, ForecastResult.scope == "company")
        .order_by(ForecastResult.generated_at.desc())
        .first()
    )
    if result is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No forecast has been run yet")
    return result
