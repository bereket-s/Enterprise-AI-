"""Employee Performance & Workforce Intelligence.

Two distinct pieces, deliberately kept separate:
  1. Performance scoring — a configurable, per-department weighted composite of KPIs.
     There is no ground truth for "performance" in general, so this is NOT a trained
     model; it is exactly the "administrator configures weights per department" engine
     described in the platform design, applied to the engagement/progression signals
     available in this public dataset (job satisfaction, environment satisfaction, job
     involvement, promotion recency). A real deployment would plug in a company's own
     sales/quality/SLA figures as additional KPIs without changing this engine.
  2. Attrition risk — a genuinely supervised model (see app.ml.attrition_model) trained
     against the dataset's real Attrition label, evaluated with precision/recall/F1/ROC-AUC.
"""
from __future__ import annotations

import joblib
import pandas as pd
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.ml import model_registry
from app.ml.attrition_model import NUMERIC_FEATURES, build_feature_matrix, train_attrition_model
from app.ml.evaluation_utils import compare_algorithms
from app.ml.generic_classifier import check_drift
from app.models.evaluation import ModelEvaluation
from app.models.workforce import Employee, KPIWeightConfig, PerformanceScore

ARTIFACT_DIR = get_settings().data_raw_dir.parent.parent / "backend" / "app" / "ml" / "artifacts"

# KPI name -> how to read/normalise it from an Employee row, to a 0-100 scale.
KPI_DEFINITIONS = {
    "job_satisfaction": lambda e: _scale_1_to_4(e.job_satisfaction),
    "environment_satisfaction": lambda e: _scale_1_to_4(e.environment_satisfaction),
    "job_involvement": lambda e: _scale_1_to_4(e.job_involvement),
    "promotion_recency": lambda e: _promotion_recency_score(e.years_since_last_promotion),
}

DEFAULT_WEIGHTS_BY_DEPARTMENT = {
    "Sales": {"job_satisfaction": 0.20, "job_involvement": 0.40, "environment_satisfaction": 0.15, "promotion_recency": 0.25},
    "Research & Development": {"job_satisfaction": 0.25, "job_involvement": 0.35, "environment_satisfaction": 0.20, "promotion_recency": 0.20},
    "Human Resources": {"job_satisfaction": 0.30, "job_involvement": 0.20, "environment_satisfaction": 0.30, "promotion_recency": 0.20},
}
FALLBACK_WEIGHTS = {"job_satisfaction": 0.25, "job_involvement": 0.25, "environment_satisfaction": 0.25, "promotion_recency": 0.25}


def _scale_1_to_4(value: float | None) -> float:
    if value is None:
        return 0.0
    return max(0.0, min(100.0, (value - 1) / 3 * 100))


def _promotion_recency_score(years: float | None) -> float:
    if years is None:
        return 50.0
    return max(0.0, 100.0 - min(years, 10.0) / 10.0 * 100.0)


def ingest_employees(db: Session, org_id: int, csv_path: str) -> dict:
    df = pd.read_csv(csv_path)
    rows = [
        Employee(
            organization_id=org_id,
            external_ref=f"EMP-{int(r.EmployeeNumber):05d}",
            full_name=f"Employee #{int(r.EmployeeNumber)}",  # dataset is synthetic; no real names
            department=str(r.Department),
            job_role=str(r.JobRole),
            age=int(r.Age),
            monthly_income=float(r.MonthlyIncome),
            years_at_company=float(r.YearsAtCompany),
            job_satisfaction=float(r.JobSatisfaction),
            environment_satisfaction=float(r.EnvironmentSatisfaction),
            job_involvement=float(r.JobInvolvement),
            years_since_last_promotion=float(r.YearsSinceLastPromotion),
            attrition_actual=bool(r.Attrition == "Yes"),
        )
        for r in df.itertuples(index=False)
    ]
    db.bulk_save_objects(rows)
    db.commit()
    return {"employees_ingested": len(rows), "departments": sorted(df["Department"].unique().tolist())}


def ingest_employees_generic(db: Session, org_id: int, df: pd.DataFrame) -> dict:
    """df has canonical columns (canonical_schemas.WORKFORCE_FIELDS). Unlike Fraud/
    Maintenance this needs no fixed-vs-generic dispatch: the Employee model's KPI
    columns were already nullable and the KPI-scoring/attrition pipeline already
    tolerates missing values, so the same ingestion and training code path serves
    the seed dataset and a company's own data equally."""
    df = df.dropna(subset=["employee_ref", "department"]).copy()

    def _opt_float(record, field):
        val = getattr(record, field, None)
        return float(val) if val is not None and not pd.isna(val) else None

    def _parse_attrition(val) -> bool | None:
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return None
        if isinstance(val, bool):
            return val
        return str(val).strip().lower() in ("yes", "true", "1")

    rows = []
    for record in df.itertuples(index=False):
        attrition = getattr(record, "attrition", None)
        rows.append(
            Employee(
                organization_id=org_id,
                external_ref=str(record.employee_ref),
                full_name=f"Employee {record.employee_ref}",
                department=str(record.department),
                job_role=str(getattr(record, "job_role", None) or ""),
                age=int(_opt_float(record, "age")) if _opt_float(record, "age") is not None else None,
                monthly_income=_opt_float(record, "monthly_income"),
                years_at_company=_opt_float(record, "years_at_company"),
                job_satisfaction=_opt_float(record, "job_satisfaction"),
                environment_satisfaction=_opt_float(record, "environment_satisfaction"),
                job_involvement=_opt_float(record, "job_involvement"),
                years_since_last_promotion=_opt_float(record, "years_since_last_promotion"),
                attrition_actual=_parse_attrition(attrition),
            )
        )
    db.bulk_save_objects(rows)
    db.commit()
    return {"employees_ingested": len(rows), "departments": sorted(df["department"].unique().tolist())}


def seed_default_kpi_weights(db: Session, org_id: int) -> int:
    departments = [d for (d,) in db.query(Employee.department).filter(Employee.organization_id == org_id).distinct()]
    existing = {
        (c.department, c.kpi_name)
        for c in db.query(KPIWeightConfig).filter(KPIWeightConfig.organization_id == org_id)
    }
    created = 0
    for dept in departments:
        weights = DEFAULT_WEIGHTS_BY_DEPARTMENT.get(dept, FALLBACK_WEIGHTS)
        for kpi_name, weight in weights.items():
            if (dept, kpi_name) in existing:
                continue
            db.add(KPIWeightConfig(organization_id=org_id, department=dept, kpi_name=kpi_name, weight=weight))
            created += 1
    db.commit()
    return created


def compute_performance_scores(db: Session, org_id: int) -> list[PerformanceScore]:
    seed_default_kpi_weights(db, org_id)
    employees = db.query(Employee).filter(Employee.organization_id == org_id).all()
    weight_rows = db.query(KPIWeightConfig).filter(KPIWeightConfig.organization_id == org_id).all()
    weights_by_dept: dict[str, dict[str, float]] = {}
    for w in weight_rows:
        weights_by_dept.setdefault(w.department, {})[w.kpi_name] = w.weight

    results = []
    for emp in employees:
        weights = weights_by_dept.get(emp.department, FALLBACK_WEIGHTS)
        breakdown = {}
        weighted_sum = 0.0
        total_weight = sum(weights.values())
        for kpi_name, weight in weights.items():
            normalized = KPI_DEFINITIONS[kpi_name](emp)
            contribution = normalized * weight
            breakdown[kpi_name] = {"normalized": round(normalized, 1), "weight": weight, "contribution": round(contribution, 1)}
            weighted_sum += contribution

        # Weights are relative, not required to sum to 1 (an admin may zero one KPI
        # out without rebalancing the rest) — normalise by total active weight so the
        # score stays on a comparable 0-100 scale regardless of how weights are split.
        total = (weighted_sum / total_weight) if total_weight > 0 else 0.0

        worst_kpi = min(breakdown.items(), key=lambda kv: kv[1]["normalized"])[0] if breakdown else None

        score = PerformanceScore(
            organization_id=org_id,
            employee_id=emp.id,
            score=round(total, 1),
            breakdown=breakdown,
            main_improvement_area=worst_kpi,
        )
        db.add(score)
        results.append(score)

    db.commit()
    for r in results:
        db.refresh(r)
    return results


def _load_as_dataframe(db: Session, org_id: int) -> pd.DataFrame:
    rows = db.query(Employee).filter(Employee.organization_id == org_id).all()
    return pd.DataFrame(
        [
            {
                "id": e.id,
                "department": e.department,
                **{f: getattr(e, f) for f in NUMERIC_FEATURES},
                "attrition_actual": e.attrition_actual,
            }
            for e in rows
        ]
    )


def train_attrition_and_score(db: Session, org_id: int) -> ModelEvaluation:
    raw = _load_as_dataframe(db, org_id)
    if raw.empty or raw["attrition_actual"].sum() < 5:
        raise ValueError("Not enough labelled attrition examples to train on")

    outcome, scores = train_attrition_model(raw)

    id_to_row = {e.id: e for e in db.query(Employee).filter(Employee.organization_id == org_id)}
    for emp_id, score in zip(raw["id"], scores):
        id_to_row[emp_id].attrition_risk_score = round(float(score), 4)

    X, y = build_feature_matrix(raw)
    scale_pos_weight = (len(y) - y.sum()) / max(1, y.sum())
    comparison = compare_algorithms(X, y, scale_pos_weight=scale_pos_weight)

    combined_metrics = {
        **outcome.metrics,
        "cross_validation": comparison["per_model"]["XGBClassifier"],
        "algorithm_comparison": comparison["per_model"],
        "significance_test": comparison["significance_test"],
    }

    evaluation = ModelEvaluation(
        organization_id=org_id,
        module_key="workforce",
        model_name="XGBoost (attrition risk)",
        metrics=combined_metrics,
        train_rows=outcome.train_rows,
        test_rows=outcome.test_rows,
    )
    db.add(evaluation)
    db.commit()
    db.refresh(evaluation)

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(outcome.model, ARTIFACT_DIR / f"attrition_model_org{org_id}.joblib")

    reference_stats = {
        col: {"mean": round(float(X[col].mean()), 4), "std": round(float(X[col].std() or 1e-6), 4)}
        for col in NUMERIC_FEATURES
    }
    model_registry.save_version(db, org_id, "workforce", outcome.model, combined_metrics, outcome.feature_columns, reference_stats)

    return evaluation


def drift_report(db: Session, org_id: int) -> dict:
    version = model_registry.get_active_version(db, org_id, "workforce")
    if version is None or not version.training_reference_stats:
        return {"drift_checked": False, "reason": "No attrition model with reference stats has been trained yet"}
    raw = _load_as_dataframe(db, org_id)
    if raw.empty:
        return {"drift_checked": False, "reason": "No employee data to check"}
    drifted = check_drift(version.training_reference_stats, raw)
    return {"drift_checked": True, "drifted_features": drifted, "model_version": version.version}
