from fastapi import APIRouter, Depends, Form, UploadFile
from sqlalchemy.orm import Session

from app.api import _ingest_helpers
from app.core.database import get_db
from app.core.deps import require_module_enabled
from app.models.bi import Product
from app.models.inventory import ReorderRecommendation
from app.schemas.bi import IngestPreview
from app.schemas.integrations import GenericIngestResult
from app.schemas.inventory import ReorderRecommendationOut
from app.services import inventory_service

router = APIRouter(
    prefix="/api/inventory",
    tags=["inventory"],
    dependencies=[Depends(require_module_enabled("inventory"))],
)


@router.post("/ingest/preview", response_model=IngestPreview)
def preview_ingest(file: UploadFile):
    return _ingest_helpers.preview("inventory", file)


@router.post("/ingest/commit", response_model=GenericIngestResult)
def commit_ingest(
    file: UploadFile,
    mapping: str = Form(...),
    org_id: int = Depends(require_module_enabled("inventory")),
    db: Session = Depends(get_db),
):
    result = _ingest_helpers.commit("inventory", db, org_id, file, mapping)
    return GenericIngestResult(records_ingested=result.get("snapshots_ingested", 0))


@router.post("/reorder/run", response_model=list[ReorderRecommendationOut])
def run_reorder_analysis(
    org_id: int = Depends(require_module_enabled("inventory")), db: Session = Depends(get_db)
):
    recs = inventory_service.generate_reorder_recommendations(db, org_id)
    return _with_product_info(db, recs)


@router.get("/reorder/latest", response_model=list[ReorderRecommendationOut])
def latest_reorder_recommendations(
    org_id: int = Depends(require_module_enabled("inventory")), db: Session = Depends(get_db)
):
    recs = (
        db.query(ReorderRecommendation)
        .filter(ReorderRecommendation.organization_id == org_id)
        .order_by(ReorderRecommendation.stockout_probability.desc())
        .all()
    )
    return _with_product_info(db, recs)


def _with_product_info(db: Session, recs: list[ReorderRecommendation]) -> list[ReorderRecommendationOut]:
    product_ids = {r.product_id for r in recs}
    products = {p.id: p for p in db.query(Product).filter(Product.id.in_(product_ids)).all()}
    out = []
    for r in recs:
        p = products[r.product_id]
        out.append(
            ReorderRecommendationOut(
                id=r.id,
                product_id=r.product_id,
                product_sku=p.sku,
                product_name=p.name,
                expected_demand=r.expected_demand,
                current_stock=r.current_stock,
                safety_stock=r.safety_stock,
                reorder_point=r.reorder_point,
                recommended_order_qty=r.recommended_order_qty,
                stockout_probability=r.stockout_probability,
                risk_label=r.risk_label,
            )
        )
    return out
