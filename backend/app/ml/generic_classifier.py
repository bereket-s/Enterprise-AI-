"""A schema-agnostic classifier trainer for "bring your own data" ingestion.

The dataset-specific trainers (fraud_model.py, maintenance_model.py,
attrition_model.py) assume the exact public-dataset schema used for this
capstone's evaluation. A real company's own data won't have V1..V28 PCA
features or five specific sensor columns — so this module trains on *whatever*
numeric/categorical columns the company's data actually has, reusing the same
cross-validation and algorithm-comparison machinery (evaluation_utils.py) that
the fixed-schema trainers use, just over a dynamically-built feature matrix.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

from app.ml.evaluation_utils import compare_algorithms


@dataclass
class GenericModelOutcome:
    model: XGBClassifier
    metrics: dict
    train_rows: int
    test_rows: int
    feature_columns: list[str]
    reference_stats: dict  # {numeric_col: {"mean": .., "std": ..}} computed on training rows only


def build_feature_matrix(
    df: pd.DataFrame, numeric_cols: list[str], categorical_cols: list[str]
) -> tuple[pd.DataFrame, list[str]]:
    work = df.copy()
    for col in numeric_cols:
        work[col] = pd.to_numeric(work[col], errors="coerce")
        work[col] = work[col].fillna(work[col].mean())

    if categorical_cols:
        work = pd.get_dummies(work, columns=categorical_cols, prefix=categorical_cols)
        dummy_cols = [c for c in work.columns if any(c.startswith(f"{cc}_") for cc in categorical_cols)]
    else:
        dummy_cols = []

    feature_cols = numeric_cols + dummy_cols
    return work[feature_cols].fillna(0), feature_cols


def train_generic_classifier(
    df: pd.DataFrame,
    target_col: str,
    numeric_cols: list[str],
    categorical_cols: list[str] | None = None,
    seed: int = 42,
) -> tuple[GenericModelOutcome, pd.Series, dict]:
    """Returns (outcome, per-row risk scores aligned to df.index, cross-validation+comparison dict)."""
    categorical_cols = categorical_cols or []
    if not numeric_cols and not categorical_cols:
        raise ValueError("At least one numeric or categorical feature column is required to train a model")

    X, feature_cols = build_feature_matrix(df, numeric_cols, categorical_cols)
    y = df[target_col].astype(int)

    if y.sum() < 5 or (len(y) - y.sum()) < 5:
        raise ValueError("Need at least 5 positive and 5 negative labelled examples to train a classifier")

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
        "positive_rate_in_data": round(float(y.mean()), 5),
    }

    reference_stats = {
        col: {"mean": round(float(X_train[col].mean()), 4), "std": round(float(X_train[col].std() or 1e-6), 4)}
        for col in numeric_cols
    }

    outcome = GenericModelOutcome(
        model=model, metrics=metrics, train_rows=len(X_train), test_rows=len(X_test),
        feature_columns=feature_cols, reference_stats=reference_stats,
    )

    all_scores = pd.Series(model.predict_proba(X)[:, 1], index=df.index)

    scale_pos_weight_full = (len(y) - y.sum()) / max(1, y.sum())
    comparison = compare_algorithms(X, y, scale_pos_weight=scale_pos_weight_full)

    return outcome, all_scores, comparison


def check_drift(reference_stats: dict, new_batch: pd.DataFrame, threshold_std: float = 2.0) -> dict:
    """Flags features whose mean in a new scoring batch has shifted by more than
    `threshold_std` training-set standard deviations from the training mean — a
    simple, cheap drift signal appropriate for a scheduled-retrain trigger."""
    drifted = {}
    for col, stats in reference_stats.items():
        if col not in new_batch.columns:
            continue
        new_mean = pd.to_numeric(new_batch[col], errors="coerce").mean()
        if new_mean is None or np.isnan(new_mean):
            continue
        std = stats["std"] or 1e-6
        shift = abs(new_mean - stats["mean"]) / std
        if shift >= threshold_std:
            drifted[col] = {"training_mean": stats["mean"], "current_mean": round(float(new_mean), 4), "shift_std": round(float(shift), 2)}
    return drifted
