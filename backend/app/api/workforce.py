from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api import _ingest_helpers
from app.core.database import get_db
from app.core.deps import require_module_enabled
from app.models.evaluation import ModelEvaluation
from app.models.workforce import Employee, Goal, KPIWeightConfig, PerformanceScore
from app.schemas.bi import IngestPreview
from app.schemas.fraud import EvaluationOut
from app.schemas.integrations import GenericIngestResult
from app.schemas.workforce import (
    EmployeeOut,
    GoalCreate,
    GoalOut,
    KPIWeightOut,
    KPIWeightUpdate,
    PerformanceScoreOut,
)
from app.services import workforce_service

router = APIRouter(
    prefix="/api/workforce",
    tags=["workforce"],
    dependencies=[Depends(require_module_enabled("workforce"))],
)


@router.post("/ingest/preview", response_model=IngestPreview)
def preview_ingest(file: UploadFile):
    return _ingest_helpers.preview("workforce", file)


@router.post("/ingest/commit", response_model=GenericIngestResult)
def commit_ingest(
    file: UploadFile,
    mapping: str = Form(...),
    org_id: int = Depends(require_module_enabled("workforce")),
    db: Session = Depends(get_db),
):
    result = _ingest_helpers.commit("workforce", db, org_id, file, mapping)
    return GenericIngestResult(records_ingested=result.get("employees_ingested", 0))


@router.get("/employees", response_model=list[EmployeeOut])
def list_employees(
    department: str | None = None,
    org_id: int = Depends(require_module_enabled("workforce")),
    db: Session = Depends(get_db),
):
    query = db.query(Employee).filter(Employee.organization_id == org_id)
    if department:
        query = query.filter(Employee.department == department)
    return query.all()


@router.get("/kpi-weights", response_model=list[KPIWeightOut])
def list_kpi_weights(org_id: int = Depends(require_module_enabled("workforce")), db: Session = Depends(get_db)):
    workforce_service.seed_default_kpi_weights(db, org_id)
    return db.query(KPIWeightConfig).filter(KPIWeightConfig.organization_id == org_id).all()


@router.put("/kpi-weights/{department}/{kpi_name}", response_model=KPIWeightOut)
def set_kpi_weight(
    department: str,
    kpi_name: str,
    payload: KPIWeightUpdate,
    org_id: int = Depends(require_module_enabled("workforce")),
    db: Session = Depends(get_db),
):
    """Lets an org_admin re-weight a department's KPIs — the "each company defines its
    own KPIs and weights" requirement from the platform design."""
    row = (
        db.query(KPIWeightConfig)
        .filter(
            KPIWeightConfig.organization_id == org_id,
            KPIWeightConfig.department == department,
            KPIWeightConfig.kpi_name == kpi_name,
        )
        .first()
    )
    if row is None:
        if kpi_name not in workforce_service.KPI_DEFINITIONS:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unknown KPI '{kpi_name}'")
        row = KPIWeightConfig(organization_id=org_id, department=department, kpi_name=kpi_name, weight=payload.weight)
        db.add(row)
    else:
        row.weight = payload.weight
    db.commit()
    db.refresh(row)
    return row


@router.post("/performance/run", response_model=list[PerformanceScoreOut])
def run_performance_scoring(org_id: int = Depends(require_module_enabled("workforce")), db: Session = Depends(get_db)):
    return workforce_service.compute_performance_scores(db, org_id)


@router.get("/performance/{employee_id}", response_model=PerformanceScoreOut)
def latest_performance_score(
    employee_id: int, org_id: int = Depends(require_module_enabled("workforce")), db: Session = Depends(get_db)
):
    row = (
        db.query(PerformanceScore)
        .filter(PerformanceScore.organization_id == org_id, PerformanceScore.employee_id == employee_id)
        .order_by(PerformanceScore.computed_at.desc())
        .first()
    )
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No performance score computed for this employee yet")
    return row


@router.post("/attrition/train", response_model=EvaluationOut)
def train_attrition_model(org_id: int = Depends(require_module_enabled("workforce")), db: Session = Depends(get_db)):
    try:
        return workforce_service.train_attrition_and_score(db, org_id)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc


@router.get("/attrition/evaluation/latest", response_model=EvaluationOut)
def latest_attrition_evaluation(
    org_id: int = Depends(require_module_enabled("workforce")), db: Session = Depends(get_db)
):
    row = (
        db.query(ModelEvaluation)
        .filter(ModelEvaluation.organization_id == org_id, ModelEvaluation.module_key == "workforce")
        .order_by(ModelEvaluation.generated_at.desc())
        .first()
    )
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No attrition model has been trained yet")
    return row


@router.post("/goals", response_model=GoalOut, status_code=status.HTTP_201_CREATED)
def create_goal(
    payload: GoalCreate, org_id: int = Depends(require_module_enabled("workforce")), db: Session = Depends(get_db)
):
    employee = (
        db.query(Employee)
        .filter(Employee.id == payload.employee_id, Employee.organization_id == org_id)
        .first()
    )
    if employee is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Employee not found")
    goal = Goal(organization_id=org_id, **payload.model_dump())
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal


@router.get("/employees/{employee_id}/goals", response_model=list[GoalOut])
def list_goals(
    employee_id: int, org_id: int = Depends(require_module_enabled("workforce")), db: Session = Depends(get_db)
):
    return (
        db.query(Goal)
        .filter(Goal.organization_id == org_id, Goal.employee_id == employee_id)
        .all()
    )
