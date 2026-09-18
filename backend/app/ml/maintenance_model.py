"""Failure-risk classifier over the AI4I 2020 predictive maintenance sensor readings."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

NUMERIC_FEATURES = ["air_temp_k", "process_temp_k", "rotational_speed_rpm", "torque_nm", "tool_wear_min"]
TYPE_MAP = {"L": 0, "M": 1, "H": 2}  # ordinal: Low/Medium/High product quality variant
FEATURE_COLUMNS = NUMERIC_FEATURES + ["type_code"]


@dataclass
class MaintenanceModelOutcome:
    model: XGBClassifier
    metrics: dict
    train_rows: int
    test_rows: int
    feature_means: pd.Series
    feature_stds: pd.Series


def prepare_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["type_code"] = df["machine_type"].map(TYPE_MAP).fillna(1)
    return df


def train_maintenance_model(df: pd.DataFrame, seed: int = 42) -> tuple[MaintenanceModelOutcome, pd.Series]:
    """df: prepare_features() output plus an 'actual_failure' column."""
    X, y = df[FEATURE_COLUMNS], df["actual_failure"].astype(int)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=seed, stratify=y)

    n_pos = max(1, int(y_train.sum()))
    scale_pos_weight = (len(y_train) - n_pos) / n_pos

    model = XGBClassifier(
        n_estimators=250,
        max_depth=4,
        learning_rate=0.1,
        subsample=0.9,
        colsample_bytree=0.9,
        scale_pos_weight=scale_pos_weight,
        eval_metric="logloss",
        random_state=seed,
    )
    model.fit(X_train, y_train)

    proba_test = model.predict_proba(X_test)[:, 1]
    pred_test = (proba_test >= 0.5).astype(int)
    metrics = {
        "precision": round(float(precision_score(y_test, pred_test, zero_division=0)), 4),
        "recall": round(float(recall_score(y_test, pred_test, zero_division=0)), 4),
        "f1": round(float(f1_score(y_test, pred_test, zero_division=0)), 4),
        "roc_auc": round(float(roc_auc_score(y_test, proba_test)), 4),
        "failure_rate_in_data": round(float(y.mean()), 5),
    }

    healthy = df[df["actual_failure"] == 0]
    outcome = MaintenanceModelOutcome(
        model=model,
        metrics=metrics,
        train_rows=len(X_train),
        test_rows=len(X_test),
        feature_means=healthy[NUMERIC_FEATURES].mean(),
        feature_stds=healthy[NUMERIC_FEATURES].std().replace(0, 1e-6),
    )
    all_scores = pd.Series(model.predict_proba(X)[:, 1], index=df.index)
    return outcome, all_scores


def risk_label(score: float) -> str:
    if score >= 0.75:
        return "critical"
    if score >= 0.5:
        return "high"
    if score >= 0.25:
        return "medium"
    return "low"


FRIENDLY_NAMES = {
    "air_temp_k": "air temperature",
    "process_temp_k": "process temperature",
    "rotational_speed_rpm": "rotational speed",
    "torque_nm": "torque",
    "tool_wear_min": "tool wear",
}


def explain_equipment(row: pd.Series, outcome: MaintenanceModelOutcome) -> list[str]:
    z_scores = (row[NUMERIC_FEATURES] - outcome.feature_means) / outcome.feature_stds
    factors = []
    for feature, z in z_scores.sort_values(key=abs, ascending=False).items():
        if abs(z) >= 1.5:
            direction = "above" if z > 0 else "below"
            factors.append(f"{FRIENDLY_NAMES[feature]} is {abs(z):.1f} std {direction} the normal operating range")
        if len(factors) == 3:
            break
    if not factors:
        factors.append("All sensor readings are within their normal operating range")
    return factors
