"""Attrition-risk classifier — the one part of the Workforce module with ground-truth
labels (Attrition Yes/No), so it is evaluated the same way as Fraud/Maintenance.
The KPI performance-scoring engine next to it is deliberately unsupervised/configurable
(see workforce_service.py) since "performance" has no universal ground truth across
departments — that's the point of letting each org set its own KPI weights.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

NUMERIC_FEATURES = [
    "age", "monthly_income", "years_at_company", "job_satisfaction",
    "environment_satisfaction", "job_involvement", "years_since_last_promotion",
]


@dataclass
class AttritionModelOutcome:
    model: XGBClassifier
    metrics: dict
    train_rows: int
    test_rows: int
    feature_columns: list[str]


def _encode(df: pd.DataFrame) -> pd.DataFrame:
    return pd.get_dummies(df, columns=["department"], prefix="dept")


def build_feature_matrix(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Shared feature encoding so the single-split training run and the cross-validation/
    algorithm-comparison pass in evaluation_utils see exactly the same feature space."""
    encoded = _encode(df)
    feature_cols = NUMERIC_FEATURES + [c for c in encoded.columns if c.startswith("dept_")]
    X = encoded[feature_cols].fillna(0)
    y = encoded["attrition_actual"].astype(int)
    return X, y


def train_attrition_model(df: pd.DataFrame, seed: int = 42) -> tuple[AttritionModelOutcome, pd.Series]:
    """df needs NUMERIC_FEATURES + department + attrition_actual."""
    X, y = build_feature_matrix(df)
    feature_cols = list(X.columns)

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=seed, stratify=y)
    n_pos = max(1, int(y_train.sum()))
    scale_pos_weight = (len(y_train) - n_pos) / n_pos

    model = XGBClassifier(
        n_estimators=200, max_depth=4, learning_rate=0.1, subsample=0.9, colsample_bytree=0.9,
        scale_pos_weight=scale_pos_weight, eval_metric="logloss", random_state=seed,
    )
    model.fit(X_train, y_train)

    proba_test = model.predict_proba(X_test)[:, 1]
    pred_test = (proba_test >= 0.5).astype(int)
    metrics = {
        "precision": round(float(precision_score(y_test, pred_test, zero_division=0)), 4),
        "recall": round(float(recall_score(y_test, pred_test, zero_division=0)), 4),
        "f1": round(float(f1_score(y_test, pred_test, zero_division=0)), 4),
        "roc_auc": round(float(roc_auc_score(y_test, proba_test)), 4),
        "attrition_rate_in_data": round(float(y.mean()), 5),
    }
    outcome = AttritionModelOutcome(
        model=model, metrics=metrics, train_rows=len(X_train), test_rows=len(X_test), feature_columns=feature_cols
    )
    all_scores = pd.Series(model.predict_proba(X)[:, 1], index=df.index)
    return outcome, all_scores
