"""Generic demand/revenue forecasting used by both the BI and Inventory modules.

Approach: gradient-boosted regression over lag + calendar features, evaluated
against a naive last-value baseline on a held-out tail of the series. This is
documented in the report (Chapter 3/4) as the chosen method versus classical
ARIMA, chosen because it needs no extra statistics dependency and handles the
irregular, spiky retail series in the Online Retail dataset well.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from xgboost import XGBRegressor

LAGS = (1, 2, 3, 7, 14)
ROLLING_WINDOWS = (3, 7, 14)


@dataclass
class ForecastOutcome:
    model_name: str
    horizon_days: int
    mae: float
    rmse: float
    mape: float
    baseline_mae: float
    points: list[dict]  # [{date, actual, predicted}] for the evaluation window
    future_points: list[dict]  # [{date, predicted}] beyond the known series


def _build_features(series: pd.Series) -> pd.DataFrame:
    df = pd.DataFrame({"y": series})
    for lag in LAGS:
        df[f"lag_{lag}"] = df["y"].shift(lag)
    for window in ROLLING_WINDOWS:
        df[f"roll_mean_{window}"] = df["y"].shift(1).rolling(window).mean()
    df["dow"] = df.index.dayofweek
    df["day"] = df.index.day
    df["month"] = df.index.month
    df["is_weekend"] = (df.index.dayofweek >= 5).astype(int)
    return df


def _mape(actual: np.ndarray, predicted: np.ndarray) -> float:
    mask = actual != 0
    if not mask.any():
        return float("nan")
    return float(np.mean(np.abs((actual[mask] - predicted[mask]) / actual[mask])) * 100)


def forecast_daily_series(daily_series: pd.Series, horizon_days: int = 14, test_days: int = 14) -> ForecastOutcome:
    """daily_series: a pandas Series indexed by a complete daily DatetimeIndex."""
    feat = _build_features(daily_series).dropna()
    feature_cols = [c for c in feat.columns if c != "y"]

    if len(feat) < test_days + 10:
        test_days = max(3, len(feat) // 4)

    train, test = feat.iloc[:-test_days], feat.iloc[-test_days:]

    model = XGBRegressor(
        n_estimators=200, max_depth=4, learning_rate=0.08, subsample=0.9, colsample_bytree=0.9, random_state=42
    )
    model.fit(train[feature_cols], train["y"])

    pred = model.predict(test[feature_cols])
    actual = test["y"].to_numpy()
    mae = float(np.mean(np.abs(actual - pred)))
    rmse = float(np.sqrt(np.mean((actual - pred) ** 2)))
    mape = _mape(actual, pred)

    # naive baseline: "tomorrow = today"
    baseline_pred = test["lag_1"].to_numpy()
    baseline_mae = float(np.mean(np.abs(actual - baseline_pred)))

    points = [
        {"date": d.strftime("%Y-%m-%d"), "actual": float(a), "predicted": float(p)}
        for d, a, p in zip(test.index, actual, pred)
    ]

    # Recursive multi-step forecast beyond the known series.
    history = daily_series.copy()
    future_points = []
    last_date = history.index.max()
    for step in range(1, horizon_days + 1):
        next_date = last_date + pd.Timedelta(days=step)
        extended = pd.concat([history, pd.Series([np.nan], index=[next_date])])
        feat_row = _build_features(extended).iloc[[-1]][feature_cols]
        next_val = float(model.predict(feat_row)[0])
        next_val = max(next_val, 0.0)
        future_points.append({"date": next_date.strftime("%Y-%m-%d"), "predicted": next_val})
        history.loc[next_date] = next_val

    return ForecastOutcome(
        model_name="XGBoost (lag+calendar features)",
        horizon_days=horizon_days,
        mae=round(mae, 2),
        rmse=round(rmse, 2),
        mape=round(mape, 2) if not np.isnan(mape) else -1.0,
        baseline_mae=round(baseline_mae, 2),
        points=points,
        future_points=future_points,
    )
