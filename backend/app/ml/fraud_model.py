"""Supervised fraud classifier over engineered amount/geography/time features.

The source dataset (simulated card transactions, Sparkov generator) gives real
fields — merchant, category, amount, cardholder vs. merchant coordinates — so
reason codes can reference concrete signals (amount vs. this card's own average,
distance from home, time of day) instead of anonymised PCA components.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

FEATURE_COLUMNS = ["amt", "distance_km", "hour", "amt_vs_account_avg"]


@dataclass
class FraudModelOutcome:
    model: XGBClassifier
    metrics: dict
    train_rows: int
    test_rows: int
    amount_p99: float


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """df needs: amt, unix_time, cc_num, lat, long, merch_lat, merch_long."""
    df = df.copy()
    # Flat-earth approximation (fine at this scale): distance between the
    # cardholder's home coordinates and the merchant is a strong fraud signal.
    df["distance_km"] = (
        ((df["lat"] - df["merch_lat"]) * 111.0) ** 2 + ((df["long"] - df["merch_long"]) * 85.0) ** 2
    ) ** 0.5
    df["hour"] = (df["unix_time"] % 86400) // 3600
    account_avg = df.groupby("cc_num")["amt"].transform("mean")
    df["amt_vs_account_avg"] = df["amt"] / account_avg.replace(0, 1e-6)
    return df


def train_fraud_model(engineered: pd.DataFrame, seed: int = 42) -> tuple[FraudModelOutcome, pd.Series]:
    """engineered: output of engineer_features(), plus an 'is_fraud' column.

    Returns (outcome, risk_score_for_every_row) — the full-set scores are needed
    so every ingested transaction (not just the held-out test slice) gets a score.
    """
    X, y = engineered[FEATURE_COLUMNS], engineered["is_fraud"].astype(int)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=seed, stratify=y)

    n_pos = max(1, int(y_train.sum()))
    scale_pos_weight = (len(y_train) - n_pos) / n_pos

    model = XGBClassifier(
        n_estimators=250,
        max_depth=5,
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
        "fraud_rate_in_data": round(float(y.mean()), 5),
    }
    outcome = FraudModelOutcome(
        model=model,
        metrics=metrics,
        train_rows=len(X_train),
        test_rows=len(X_test),
        amount_p99=float(engineered["amt"].quantile(0.99)),
    )

    all_scores = pd.Series(model.predict_proba(X)[:, 1], index=engineered.index)
    return outcome, all_scores


def risk_label(score: float) -> str:
    if score >= 0.85:
        return "critical"
    if score >= 0.6:
        return "high"
    if score >= 0.3:
        return "medium"
    return "low"


def explain_transaction(row: pd.Series, amount_p99: float) -> list[str]:
    reasons: list[str] = []

    if row["amt"] >= amount_p99:
        reasons.append(f"Transaction amount (${row['amt']:.2f}) is in the top 1% of observed amounts.")
    if row["amt_vs_account_avg"] >= 3:
        reasons.append(f"Amount is {row['amt_vs_account_avg']:.1f}x this card's average transaction.")
    if row["distance_km"] >= 100:
        reasons.append(f"Merchant is ~{row['distance_km']:.0f}km from the cardholder's home location.")
    if int(row["hour"]) < 5:
        reasons.append(f"Transaction occurred at {int(row['hour']):02d}:00, a low-volume overnight window.")
    if not reasons:
        reasons.append("No single dominant factor; risk driven by a combination of minor signals.")
    return reasons
