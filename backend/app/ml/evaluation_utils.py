"""Shared cross-validation and multi-algorithm comparison utilities.

Used by every classification task (fraud, maintenance, attrition) so results are
reported as a mean +/- std across folds rather than a single train/test split, and
so XGBoost's choice is justified against simpler baselines rather than assumed.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

N_FOLDS = 5
RANDOM_STATE = 42


@dataclass
class CVResult:
    model_name: str
    fold_metrics: dict[str, list[float]] = field(default_factory=dict)  # metric -> [per-fold values]

    def summary(self) -> dict[str, dict[str, float]]:
        return {
            metric: {"mean": round(float(np.mean(vals)), 4), "std": round(float(np.std(vals)), 4)}
            for metric, vals in self.fold_metrics.items()
        }


def _score_fold(model, X_test, y_test) -> dict[str, float]:
    proba = model.predict_proba(X_test)[:, 1]
    pred = (proba >= 0.5).astype(int)
    return {
        "precision": precision_score(y_test, pred, zero_division=0),
        "recall": recall_score(y_test, pred, zero_division=0),
        "f1": f1_score(y_test, pred, zero_division=0),
        "roc_auc": roc_auc_score(y_test, proba) if len(set(y_test)) > 1 else float("nan"),
    }


def cross_validate_classifier(build_model, X: pd.DataFrame, y: pd.Series, n_folds: int = N_FOLDS) -> CVResult:
    """build_model: zero-arg callable returning a fresh, unfitted classifier for each fold."""
    skf = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=RANDOM_STATE)
    result = CVResult(model_name=build_model().__class__.__name__)
    for metric in ("precision", "recall", "f1", "roc_auc"):
        result.fold_metrics[metric] = []

    X_arr, y_arr = X.reset_index(drop=True), y.reset_index(drop=True)
    for train_idx, test_idx in skf.split(X_arr, y_arr):
        X_train, X_test = X_arr.iloc[train_idx], X_arr.iloc[test_idx]
        y_train, y_test = y_arr.iloc[train_idx], y_arr.iloc[test_idx]

        model = build_model()
        model.fit(X_train, y_train)
        scores = _score_fold(model, X_test, y_test)
        for metric, value in scores.items():
            result.fold_metrics[metric].append(value)

    return result


def compare_algorithms(X: pd.DataFrame, y: pd.Series, scale_pos_weight: float, n_folds: int = N_FOLDS) -> dict:
    """Cross-validate XGBoost against Logistic Regression and Random Forest baselines,
    and run a paired statistical test (Wilcoxon signed-rank on per-fold ROC-AUC) to check
    whether XGBoost's advantage (if any) is unlikely to be due to chance across folds.
    """

    def xgb_builder():
        return XGBClassifier(
            n_estimators=200, max_depth=4, learning_rate=0.1, subsample=0.9, colsample_bytree=0.9,
            scale_pos_weight=scale_pos_weight, eval_metric="logloss", random_state=RANDOM_STATE,
        )

    def logreg_builder():
        # Logistic regression needs scaled features to converge reliably; wrap in a
        # tiny pipeline-like object exposing fit/predict_proba.
        class ScaledLogReg:
            def __init__(self):
                self.scaler = StandardScaler()
                self.model = LogisticRegression(max_iter=2000, class_weight="balanced", random_state=RANDOM_STATE)

            def fit(self, X, y):
                Xs = self.scaler.fit_transform(X)
                self.model.fit(Xs, y)
                return self

            def predict_proba(self, X):
                return self.model.predict_proba(self.scaler.transform(X))

            def __class__prop(self):
                return "LogisticRegression"

        inst = ScaledLogReg()
        inst.__class__.__name__ = "LogisticRegression"
        return inst

    def rf_builder():
        return RandomForestClassifier(
            n_estimators=200, max_depth=8, class_weight="balanced", random_state=RANDOM_STATE, n_jobs=-1
        )

    results = {}
    fold_auc_by_model = {}
    for builder in (xgb_builder, logreg_builder, rf_builder):
        cv = cross_validate_classifier(builder, X, y, n_folds=n_folds)
        results[cv.model_name] = cv.summary()
        fold_auc_by_model[cv.model_name] = cv.fold_metrics["roc_auc"]

    # Paired Wilcoxon signed-rank test: XGBoost vs. the strongest baseline, on matched
    # per-fold ROC-AUC values (same folds for every model, so pairing is valid).
    baseline_name = max(
        (name for name in fold_auc_by_model if name != "XGBClassifier"),
        key=lambda n: np.mean(fold_auc_by_model[n]),
    )
    xgb_scores = fold_auc_by_model["XGBClassifier"]
    baseline_scores = fold_auc_by_model[baseline_name]
    try:
        stat, p_value = stats.wilcoxon(xgb_scores, baseline_scores)
    except ValueError:
        # Wilcoxon requires at least one non-zero difference; identical scores across
        # all folds (rare, but possible with tiny fold counts) would otherwise raise.
        stat, p_value = float("nan"), float("nan")

    return {
        "per_model": results,
        "significance_test": {
            "test": "wilcoxon_signed_rank",
            "compared": f"XGBClassifier vs {baseline_name}",
            "statistic": round(float(stat), 4) if stat == stat else None,
            "p_value": round(float(p_value), 4) if p_value == p_value else None,
            "n_folds": n_folds,
        },
    }
