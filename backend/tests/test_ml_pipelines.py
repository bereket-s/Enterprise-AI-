"""Fast sanity checks for each module's ML pipeline against small synthetic data —
these don't touch the database or the large public CSVs, just the pure functions.
"""
import numpy as np
import pandas as pd

from app.ml.attrition_model import train_attrition_model
from app.ml.evaluation_utils import compare_algorithms, cross_validate_classifier
from app.ml.fraud_model import engineer_features, explain_transaction, risk_label, train_fraud_model
from app.ml.maintenance_model import prepare_features, train_maintenance_model
from app.ml.timeseries import forecast_daily_series


def test_forecast_daily_series_returns_sane_metrics():
    rng = np.random.default_rng(0)
    dates = pd.date_range("2024-01-01", periods=120, freq="D")
    values = 100 + 10 * np.sin(np.arange(120) / 7) + rng.normal(0, 2, 120)
    series = pd.Series(values, index=dates)

    outcome = forecast_daily_series(series, horizon_days=7, test_days=14)

    assert outcome.mae >= 0
    assert outcome.rmse >= outcome.mae * 0.5  # RMSE should not be wildly smaller than MAE
    assert len(outcome.future_points) == 7
    assert all(p["predicted"] >= 0 for p in outcome.future_points)


def test_fraud_model_trains_and_scores():
    rng = np.random.default_rng(1)
    n = 500
    df = pd.DataFrame(
        {
            "amt": rng.exponential(50, n),
            "unix_time": rng.integers(0, 86400 * 30, n),
            "cc_num": rng.integers(1000, 1010, n).astype(str),
            "lat": rng.uniform(30, 40, n),
            "long": rng.uniform(-100, -90, n),
            "merch_lat": rng.uniform(30, 40, n),
            "merch_long": rng.uniform(-100, -90, n),
        }
    )
    df["is_fraud"] = (rng.random(n) < 0.1).astype(int)
    df.loc[df["is_fraud"] == 1, "amt"] *= 10  # give the model a learnable signal

    engineered = engineer_features(df)
    outcome, scores = train_fraud_model(engineered)

    assert 0 <= outcome.metrics["roc_auc"] <= 1
    assert len(scores) == n
    assert all(0 <= s <= 1 for s in scores)

    sample_row = engineered.iloc[0]
    reasons = explain_transaction(sample_row, outcome.amount_p99)
    assert isinstance(reasons, list) and len(reasons) >= 1
    assert risk_label(0.9) == "critical"
    assert risk_label(0.1) == "low"


def test_maintenance_model_trains_and_scores():
    rng = np.random.default_rng(2)
    n = 400
    df = pd.DataFrame(
        {
            "machine_type": rng.choice(["L", "M", "H"], n),
            "air_temp_k": rng.normal(298, 2, n),
            "process_temp_k": rng.normal(308, 2, n),
            "rotational_speed_rpm": rng.normal(1500, 100, n),
            "torque_nm": rng.normal(40, 8, n),
            "tool_wear_min": rng.uniform(0, 200, n),
        }
    )
    df["actual_failure"] = ((df["tool_wear_min"] > 180) | (rng.random(n) < 0.02)).astype(int)

    prepared = prepare_features(df)
    outcome, scores = train_maintenance_model(prepared)

    assert 0 <= outcome.metrics["roc_auc"] <= 1
    assert len(scores) == n


def test_attrition_model_trains_and_scores():
    rng = np.random.default_rng(3)
    n = 400
    df = pd.DataFrame(
        {
            "department": rng.choice(["Sales", "Research & Development", "Human Resources"], n),
            "age": rng.integers(20, 60, n),
            "monthly_income": rng.integers(2000, 15000, n),
            "years_at_company": rng.integers(0, 20, n),
            "job_satisfaction": rng.integers(1, 5, n),
            "environment_satisfaction": rng.integers(1, 5, n),
            "job_involvement": rng.integers(1, 5, n),
            "years_since_last_promotion": rng.integers(0, 10, n),
        }
    )
    df["attrition_actual"] = ((df["job_satisfaction"] <= 1) | (rng.random(n) < 0.05)).astype(int)

    outcome, scores = train_attrition_model(df)

    assert 0 <= outcome.metrics["roc_auc"] <= 1
    assert len(scores) == n


def _make_learnable_classification_frame(n=600, seed=7):
    rng = np.random.default_rng(seed)
    X = pd.DataFrame({"f1": rng.normal(0, 1, n), "f2": rng.normal(0, 1, n), "f3": rng.normal(0, 1, n)})
    # y depends mostly on f1 so a real classifier should clearly beat chance (AUC > 0.5).
    logits = 3 * X["f1"] + rng.normal(0, 0.5, n)
    y = pd.Series((logits > np.median(logits)).astype(int))
    return X, y


def test_cross_validate_classifier_returns_per_fold_metrics():
    from xgboost import XGBClassifier

    X, y = _make_learnable_classification_frame()
    result = cross_validate_classifier(lambda: XGBClassifier(n_estimators=50, max_depth=3, random_state=42), X, y)

    summary = result.summary()
    assert set(summary.keys()) == {"precision", "recall", "f1", "roc_auc"}
    for metric_summary in summary.values():
        assert "mean" in metric_summary and "std" in metric_summary
    assert len(result.fold_metrics["roc_auc"]) == 5
    # A genuinely learnable signal should clearly beat random guessing on average.
    assert summary["roc_auc"]["mean"] > 0.7


def test_compare_algorithms_runs_all_three_models_with_significance_test():
    X, y = _make_learnable_classification_frame()
    scale_pos_weight = (len(y) - y.sum()) / max(1, y.sum())

    result = compare_algorithms(X, y, scale_pos_weight=scale_pos_weight, n_folds=3)

    assert set(result["per_model"].keys()) == {"XGBClassifier", "LogisticRegression", "RandomForestClassifier"}
    for model_summary in result["per_model"].values():
        assert "roc_auc" in model_summary

    sig = result["significance_test"]
    assert sig["test"] == "wilcoxon_signed_rank"
    assert sig["n_folds"] == 3
    assert "XGBClassifier vs" in sig["compared"]
