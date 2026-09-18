from __future__ import annotations

import joblib
import pandas as pd
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.ml import model_registry
from app.ml.evaluation_utils import compare_algorithms
from app.ml.fraud_model import FEATURE_COLUMNS, engineer_features, explain_transaction, risk_label, train_fraud_model
from app.ml.generic_classifier import build_feature_matrix, check_drift, train_generic_classifier
from app.models.evaluation import ModelEvaluation
from app.models.fraud import FraudTransaction

settings = get_settings()
ARTIFACT_DIR = get_settings().data_raw_dir.parent.parent / "backend" / "app" / "ml" / "artifacts"

# The exact keys the seeded (Sparkov) demo dataset always populates. Any row
# missing one of these came from a "bring your own data" integration instead of
# the capstone's own seed script, and is routed to the generic trainer below.
_FIXED_SCHEMA_KEYS = {"amt", "unix_time", "cc_num", "lat", "long", "merch_lat", "merch_long"}


def ingest_fraud_sample(db: Session, org_id: int, csv_path: str) -> dict:
    df = pd.read_csv(csv_path)
    df["trans_date_trans_time"] = pd.to_datetime(df["trans_date_trans_time"])

    rows = []
    for i, record in enumerate(df.itertuples(index=False)):
        rows.append(
            FraudTransaction(
                organization_id=org_id,
                external_ref=f"TXN-{i:06d}",
                amount=float(record.amt),
                occurred_at=record.trans_date_trans_time.to_pydatetime(),
                features={
                    "amt": float(record.amt),
                    "unix_time": float(record.unix_time),
                    "cc_num": str(record.cc_num),
                    "merchant": str(record.merchant),
                    "category": str(record.category),
                    "city": str(record.city),
                    "state": str(record.state),
                    "lat": float(record.lat),
                    "long": float(record.long),
                    "merch_lat": float(record.merch_lat),
                    "merch_long": float(record.merch_long),
                },
                actual_is_fraud=bool(record.is_fraud),
                status="pending",
            )
        )
    db.bulk_save_objects(rows)
    db.commit()
    return {"transactions_ingested": len(rows), "fraud_rate": round(float(df["is_fraud"].mean()), 4)}


def ingest_fraud_generic(db: Session, org_id: int, df: pd.DataFrame) -> dict:
    """df has canonical columns (app/services/canonical_schemas.py: FRAUD_FIELDS) —
    the shape produced by *every* integration path (upload, DB pull, API push,
    webhook, connector) once suggest_mapping() has resolved a company's own field
    names. Only amount/timestamp/account_ref are required; everything else is
    stored when present and simply unused in feature engineering when absent.
    """
    df = df.dropna(subset=["amount", "timestamp", "account_ref"]).copy()
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["amount", "timestamp"])

    optional_numeric = ["customer_lat", "customer_long", "merchant_lat", "merchant_long"]
    rows = []
    for i, record in enumerate(df.itertuples(index=False)):
        features = {"amount": float(record.amount), "account_ref": str(record.account_ref)}
        for col in optional_numeric:
            val = getattr(record, col, None)
            if val is not None and not pd.isna(val):
                features[col] = float(val)
        for col in ("merchant", "category"):
            val = getattr(record, col, None)
            if val is not None and not pd.isna(val):
                features[col] = str(val)

        rows.append(
            FraudTransaction(
                organization_id=org_id,
                external_ref=str(getattr(record, "transaction_ref", None) or f"BYOD-{i:06d}"),
                amount=float(record.amount),
                occurred_at=record.timestamp.to_pydatetime(),
                features=features,
                actual_is_fraud=bool(getattr(record, "is_fraud", False)) if hasattr(record, "is_fraud") else None,
                status="pending",
            )
        )
    db.bulk_save_objects(rows)
    db.commit()
    return {"transactions_ingested": len(rows)}


def _load_as_dataframe(db: Session, org_id: int) -> tuple[pd.DataFrame, bool]:
    """Returns (dataframe, is_fixed_schema). is_fixed_schema is True only if every
    row has the full Sparkov-style key set, in which case the original
    hand-engineered fraud_model.py pipeline (and its already-reported Chapter 4
    results) is used unchanged; otherwise the generic trainer is used."""
    txns = db.query(FraudTransaction).filter(FraudTransaction.organization_id == org_id).all()
    if not txns:
        return pd.DataFrame(), True

    is_fixed_schema = all(_FIXED_SCHEMA_KEYS.issubset(t.features.keys()) for t in txns)

    if is_fixed_schema:
        records = [
            {
                "id": t.id, "amt": t.features["amt"], "unix_time": t.features["unix_time"],
                "cc_num": t.features["cc_num"], "lat": t.features["lat"], "long": t.features["long"],
                "merch_lat": t.features["merch_lat"], "merch_long": t.features["merch_long"],
                "is_fraud": int(t.actual_is_fraud),
            }
            for t in txns
        ]
    else:
        records = [
            {
                "id": t.id,
                "amount": t.features.get("amount", t.amount),
                "hour": (t.occurred_at.hour if t.occurred_at else 0),
                "account_ref": t.features.get("account_ref"),
                "has_geo": all(k in t.features for k in ("customer_lat", "customer_long", "merchant_lat", "merchant_long")),
                "customer_lat": t.features.get("customer_lat"),
                "customer_long": t.features.get("customer_long"),
                "merchant_lat": t.features.get("merchant_lat"),
                "merchant_long": t.features.get("merchant_long"),
                "is_fraud": int(bool(t.actual_is_fraud)),
            }
            for t in txns
        ]
    return pd.DataFrame(records), is_fixed_schema


def train_and_score(db: Session, org_id: int) -> ModelEvaluation:
    raw, is_fixed_schema = _load_as_dataframe(db, org_id)
    if raw.empty or raw["is_fraud"].sum() < 5:
        raise ValueError("Not enough labelled fraud examples to train on")

    id_to_row = {t.id: t for t in db.query(FraudTransaction).filter(FraudTransaction.organization_id == org_id)}

    if is_fixed_schema:
        engineered = engineer_features(raw)
        outcome, scores = train_fraud_model(engineered)

        for (_, row), score in zip(engineered.iterrows(), scores):
            txn = id_to_row[row["id"]]
            txn.risk_score = round(float(score), 4)
            txn.risk_label = risk_label(float(score))
            txn.reason_codes = explain_transaction(row, outcome.amount_p99)

        X, y = engineered[FEATURE_COLUMNS], engineered["is_fraud"].astype(int)
        scale_pos_weight = (len(y) - y.sum()) / max(1, y.sum())
        comparison = compare_algorithms(X, y, scale_pos_weight=scale_pos_weight)
        model_name = "XGBoost (amount/geo/time engineered features)"
        feature_columns = FEATURE_COLUMNS
        reference_stats = {}
        trained_model = outcome.model
        metrics, train_rows, test_rows = outcome.metrics, outcome.train_rows, outcome.test_rows
    else:
        # Bring-your-own-data path: engineer whatever's actually available.
        engineered = raw.copy()
        numeric_cols = ["amount", "hour"]
        if engineered["has_geo"].all():
            engineered["distance_km"] = (
                ((engineered["customer_lat"] - engineered["merchant_lat"]) * 111.0) ** 2
                + ((engineered["customer_long"] - engineered["merchant_long"]) * 85.0) ** 2
            ) ** 0.5
            numeric_cols.append("distance_km")
        if engineered["account_ref"].notna().any():
            account_avg = engineered.groupby("account_ref")["amount"].transform("mean")
            engineered["amount_vs_account_avg"] = engineered["amount"] / account_avg.replace(0, 1e-6)
            numeric_cols.append("amount_vs_account_avg")

        outcome, scores, comparison = train_generic_classifier(engineered, "is_fraud", numeric_cols)
        amount_p99 = float(engineered["amount"].quantile(0.99))

        for (_, row), score in zip(engineered.iterrows(), scores):
            txn = id_to_row[row["id"]]
            txn.risk_score = round(float(score), 4)
            txn.risk_label = risk_label(float(score))
            reasons = []
            if row["amount"] >= amount_p99:
                reasons.append(f"Transaction amount (${row['amount']:.2f}) is in the top 1% of observed amounts.")
            if "amount_vs_account_avg" in row and row["amount_vs_account_avg"] >= 3:
                reasons.append(f"Amount is {row['amount_vs_account_avg']:.1f}x this account's average transaction.")
            if "distance_km" in row and row["distance_km"] >= 100:
                reasons.append(f"Merchant is ~{row['distance_km']:.0f}km from the account's usual location.")
            txn.reason_codes = reasons or ["No single dominant factor; risk driven by a combination of minor signals."]

        model_name = "XGBoost (generic bring-your-own-data features)"
        feature_columns = outcome.feature_columns
        reference_stats = outcome.reference_stats
        trained_model = outcome.model
        metrics, train_rows, test_rows = outcome.metrics, outcome.train_rows, outcome.test_rows

    combined_metrics = {
        **metrics,
        "cross_validation": comparison["per_model"]["XGBClassifier"],
        "algorithm_comparison": comparison["per_model"],
        "significance_test": comparison["significance_test"],
    }

    evaluation = ModelEvaluation(
        organization_id=org_id, module_key="fraud", model_name=model_name,
        metrics=combined_metrics, train_rows=train_rows, test_rows=test_rows,
    )
    db.add(evaluation)
    db.commit()
    db.refresh(evaluation)

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(trained_model, ARTIFACT_DIR / f"fraud_model_org{org_id}.joblib")
    model_registry.save_version(db, org_id, "fraud", trained_model, combined_metrics, feature_columns, reference_stats)

    return evaluation


def drift_report(db: Session, org_id: int) -> dict:
    """Compares the current live transaction batch against the active model's
    training-time feature statistics — the "drift monitoring" gap from
    docs/architecture.md §10, exposed for a scheduled-retrain trigger to consult."""
    version = model_registry.get_active_version(db, org_id, "fraud")
    if version is None or not version.training_reference_stats:
        return {"drift_checked": False, "reason": "No generic-schema model with reference stats has been trained yet"}
    raw, is_fixed_schema = _load_as_dataframe(db, org_id)
    if is_fixed_schema or raw.empty:
        return {"drift_checked": False, "reason": "Drift monitoring applies to the generic bring-your-own-data path"}
    drifted = check_drift(version.training_reference_stats, raw)
    return {"drift_checked": True, "drifted_features": drifted, "model_version": version.version}
