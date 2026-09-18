from __future__ import annotations

import joblib
import pandas as pd
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.ml import model_registry
from app.ml.evaluation_utils import compare_algorithms
from app.ml.generic_classifier import check_drift, train_generic_classifier
from app.ml.maintenance_model import (
    FEATURE_COLUMNS,
    explain_equipment,
    prepare_features,
    risk_label,
    train_maintenance_model,
)
from app.models.evaluation import ModelEvaluation
from app.models.maintenance import Equipment

ARTIFACT_DIR = get_settings().data_raw_dir.parent.parent / "backend" / "app" / "ml" / "artifacts"

_SOURCE_COLUMNS = {
    "Product ID": "external_ref",
    "Type": "machine_type",
    "Air temperature [K]": "air_temp_k",
    "Process temperature [K]": "process_temp_k",
    "Rotational speed [rpm]": "rotational_speed_rpm",
    "Torque [Nm]": "torque_nm",
    "Tool wear [min]": "tool_wear_min",
    "Machine failure": "actual_failure",
}
_FIXED_SCHEMA_COLUMNS = ["air_temp_k", "process_temp_k", "rotational_speed_rpm", "torque_nm", "tool_wear_min"]
# Canonical BYOD field -> the Equipment column with the closest natural meaning.
_CANONICAL_TO_FIXED_COLUMN = {
    "temperature": "air_temp_k",
    "rotational_speed": "rotational_speed_rpm",
    "torque": "torque_nm",
    "tool_wear": "tool_wear_min",
}
_EXTRA_READING_FIELDS = ["vibration", "pressure"]


def ingest_equipment_sample(db: Session, org_id: int, csv_path: str, sample_size: int = 4000, seed: int = 42) -> dict:
    df = pd.read_csv(csv_path)
    if len(df) > sample_size:
        df = df.sample(n=sample_size, random_state=seed).reset_index(drop=True)
    df = df.rename(columns=_SOURCE_COLUMNS)

    rows = [
        Equipment(
            organization_id=org_id,
            external_ref=str(record.external_ref),
            machine_type=str(record.machine_type),
            air_temp_k=float(record.air_temp_k),
            process_temp_k=float(record.process_temp_k),
            rotational_speed_rpm=float(record.rotational_speed_rpm),
            torque_nm=float(record.torque_nm),
            tool_wear_min=float(record.tool_wear_min),
            actual_failure=bool(record.actual_failure),
        )
        for record in df.itertuples(index=False)
    ]
    db.bulk_save_objects(rows)
    db.commit()
    return {"equipment_ingested": len(rows), "failure_rate": round(float(df["actual_failure"].mean()), 4)}


def ingest_equipment_generic(db: Session, org_id: int, df: pd.DataFrame) -> dict:
    """df has canonical columns (canonical_schemas.MAINTENANCE_FIELDS). Only
    equipment_ref is required; at least one sensor reading should be present or
    the row carries no signal to train or score from."""
    df = df.dropna(subset=["equipment_ref"]).copy()

    rows = []
    for record in df.itertuples(index=False):
        extra = {}
        for field in _EXTRA_READING_FIELDS:
            val = getattr(record, field, None)
            if val is not None and not pd.isna(val):
                extra[field] = float(val)

        def _fixed(field: str) -> float | None:
            val = getattr(record, field, None)
            return float(val) if val is not None and not pd.isna(val) else None

        failure = getattr(record, "failure", None)
        rows.append(
            Equipment(
                organization_id=org_id,
                external_ref=str(record.equipment_ref),
                machine_type=str(getattr(record, "machine_type", None) or "M"),
                air_temp_k=_fixed("temperature"),
                process_temp_k=None,
                rotational_speed_rpm=_fixed("rotational_speed"),
                torque_nm=_fixed("torque"),
                tool_wear_min=_fixed("tool_wear"),
                extra_readings=extra,
                actual_failure=bool(failure) if failure is not None and not pd.isna(failure) else None,
            )
        )
    db.bulk_save_objects(rows)
    db.commit()
    return {"equipment_ingested": len(rows)}


def _load_as_dataframe(db: Session, org_id: int) -> tuple[pd.DataFrame, bool]:
    rows = db.query(Equipment).filter(Equipment.organization_id == org_id).all()
    if not rows:
        return pd.DataFrame(), True

    is_fixed_schema = all(getattr(r, col) is not None for r in rows for col in _FIXED_SCHEMA_COLUMNS)

    records = []
    for r in rows:
        rec = {
            "id": r.id, "machine_type": r.machine_type, "air_temp_k": r.air_temp_k,
            "process_temp_k": r.process_temp_k, "rotational_speed_rpm": r.rotational_speed_rpm,
            "torque_nm": r.torque_nm, "tool_wear_min": r.tool_wear_min,
            "actual_failure": r.actual_failure,
        }
        rec.update(r.extra_readings or {})
        records.append(rec)
    return pd.DataFrame(records), is_fixed_schema


def train_and_score(db: Session, org_id: int) -> ModelEvaluation:
    raw, is_fixed_schema = _load_as_dataframe(db, org_id)
    if raw.empty or raw["actual_failure"].sum() < 5:
        raise ValueError("Not enough labelled failure examples to train on")

    id_to_row = {r.id: r for r in db.query(Equipment).filter(Equipment.organization_id == org_id)}

    if is_fixed_schema:
        prepared = prepare_features(raw)
        outcome, scores = train_maintenance_model(prepared)

        for (_, row), score in zip(prepared.iterrows(), scores):
            eq = id_to_row[row["id"]]
            eq.failure_risk_score = round(float(score), 4)
            eq.risk_label = risk_label(float(score))
            eq.contributing_factors = explain_equipment(row, outcome)

        X, y = prepared[FEATURE_COLUMNS], prepared["actual_failure"].astype(int)
        scale_pos_weight = (len(y) - y.sum()) / max(1, y.sum())
        comparison = compare_algorithms(X, y, scale_pos_weight=scale_pos_weight)
        model_name, feature_columns, reference_stats = "XGBoost (sensor readings)", FEATURE_COLUMNS, {}
        trained_model = outcome.model
        metrics, train_rows, test_rows = outcome.metrics, outcome.train_rows, outcome.test_rows
    else:
        numeric_cols = [c for c in raw.columns if c not in ("id", "machine_type", "actual_failure") and raw[c].notna().any()]
        categorical_cols = ["machine_type"] if raw["machine_type"].notna().any() else []
        prepared = raw.copy()
        prepared["actual_failure"] = prepared["actual_failure"].fillna(False)

        outcome, scores, comparison = train_generic_classifier(prepared, "actual_failure", numeric_cols, categorical_cols)

        for (_, row), score in zip(prepared.iterrows(), scores):
            eq = id_to_row[row["id"]]
            eq.failure_risk_score = round(float(score), 4)
            eq.risk_label = risk_label(float(score))
            factors = []
            for col in numeric_cols:
                ref = outcome.reference_stats.get(col)
                if not ref or ref["std"] == 0:
                    continue
                z = (row[col] - ref["mean"]) / ref["std"]
                if abs(z) >= 1.5:
                    factors.append(f"{col.replace('_', ' ')} is {abs(z):.1f} std {'above' if z > 0 else 'below'} the normal operating range")
            eq.contributing_factors = factors[:3] or ["All sensor readings are within their normal operating range"]

        model_name = "XGBoost (generic bring-your-own-data sensor readings)"
        feature_columns, reference_stats = outcome.feature_columns, outcome.reference_stats
        trained_model = outcome.model
        metrics, train_rows, test_rows = outcome.metrics, outcome.train_rows, outcome.test_rows

    combined_metrics = {
        **metrics,
        "cross_validation": comparison["per_model"]["XGBClassifier"],
        "algorithm_comparison": comparison["per_model"],
        "significance_test": comparison["significance_test"],
    }

    evaluation = ModelEvaluation(
        organization_id=org_id, module_key="maintenance", model_name=model_name,
        metrics=combined_metrics, train_rows=train_rows, test_rows=test_rows,
    )
    db.add(evaluation)
    db.commit()
    db.refresh(evaluation)

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(trained_model, ARTIFACT_DIR / f"maintenance_model_org{org_id}.joblib")
    model_registry.save_version(db, org_id, "maintenance", trained_model, combined_metrics, feature_columns, reference_stats)

    return evaluation


def drift_report(db: Session, org_id: int) -> dict:
    version = model_registry.get_active_version(db, org_id, "maintenance")
    if version is None or not version.training_reference_stats:
        return {"drift_checked": False, "reason": "No generic-schema model with reference stats has been trained yet"}
    raw, is_fixed_schema = _load_as_dataframe(db, org_id)
    if is_fixed_schema or raw.empty:
        return {"drift_checked": False, "reason": "Drift monitoring applies to the generic bring-your-own-data path"}
    drifted = check_drift(version.training_reference_stats, raw)
    return {"drift_checked": True, "drifted_features": drifted, "model_version": version.version}
