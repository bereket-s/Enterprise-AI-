from pydantic import BaseModel, ConfigDict


class EmployeeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    external_ref: str
    full_name: str
    department: str
    job_role: str
    attrition_risk_score: float


class PerformanceScoreOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: int
    score: float
    breakdown: dict
    main_improvement_area: str | None


class KPIWeightOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    department: str
    kpi_name: str
    weight: float


class KPIWeightUpdate(BaseModel):
    weight: float


class GoalCreate(BaseModel):
    employee_id: int
    title: str
    period: str = "Q1"
    target_value: float
    current_value: float = 0.0


class GoalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: int
    title: str
    period: str
    target_value: float
    current_value: float
    progress_pct: float
