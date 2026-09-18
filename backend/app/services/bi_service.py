from __future__ import annotations

import pandas as pd
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.ml.timeseries import ForecastOutcome, forecast_daily_series
from app.models.bi import ForecastResult, Product, SalesTransaction

CANONICAL_FIELDS = [
    "product_id",
    "product_name",
    "quantity",
    "unit_price",
    "transaction_date",
    "customer_ref",
    "country",
]


def ingest_sales_dataframe(db: Session, org_id: int, df: pd.DataFrame) -> dict:
    """df must already use canonical column names (see CANONICAL_FIELDS)."""
    df = df.dropna(subset=["product_id", "quantity", "unit_price", "transaction_date"]).copy()
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")
    df["unit_price"] = pd.to_numeric(df["unit_price"], errors="coerce")
    df["transaction_date"] = pd.to_datetime(df["transaction_date"], errors="coerce")
    df = df.dropna(subset=["quantity", "unit_price", "transaction_date"])
    df = df[(df["quantity"] > 0) & (df["unit_price"] > 0)]

    existing_products = {
        p.sku: p for p in db.query(Product).filter(Product.organization_id == org_id).all()
    }
    for sku, group in df.groupby("product_id"):
        sku = str(sku)
        if sku not in existing_products:
            name = str(group["product_name"].iloc[0]) if "product_name" in group else sku
            product = Product(organization_id=org_id, sku=sku, name=name[:255])
            db.add(product)
            db.flush()
            existing_products[sku] = product

    rows = []
    for record in df.itertuples(index=False):
        product = existing_products[str(record.product_id)]
        rows.append(
            SalesTransaction(
                organization_id=org_id,
                product_id=product.id,
                quantity=int(record.quantity),
                unit_price=float(record.unit_price),
                transaction_date=record.transaction_date.date(),
                customer_ref=str(getattr(record, "customer_ref", "") or "") or None,
                country=str(getattr(record, "country", "") or "") or None,
            )
        )
    db.bulk_save_objects(rows)
    db.commit()
    return {"products": len(existing_products), "transactions_ingested": len(rows)}


def daily_revenue_series(db: Session, org_id: int) -> pd.Series:
    rows = (
        db.query(
            SalesTransaction.transaction_date,
            func.sum(SalesTransaction.quantity * SalesTransaction.unit_price).label("revenue"),
        )
        .filter(SalesTransaction.organization_id == org_id)
        .group_by(SalesTransaction.transaction_date)
        .order_by(SalesTransaction.transaction_date)
        .all()
    )
    if not rows:
        return pd.Series(dtype=float)

    df = pd.DataFrame(rows, columns=["date", "revenue"])
    df["date"] = pd.to_datetime(df["date"])
    series = df.set_index("date")["revenue"].asfreq("D").fillna(0.0)
    return series


def compute_kpis(db: Session, org_id: int) -> dict:
    series = daily_revenue_series(db, org_id)
    if series.empty:
        return {"total_revenue": 0, "avg_daily_revenue": 0, "trend_pct": 0, "days_of_history": 0, "top_products": []}

    total_revenue = float(series.sum())
    avg_daily = float(series.mean())

    half = len(series) // 2
    first_half_avg = series.iloc[:half].mean() if half > 0 else series.mean()
    second_half_avg = series.iloc[half:].mean()
    trend_pct = (
        round(100 * (second_half_avg - first_half_avg) / first_half_avg, 1) if first_half_avg else 0.0
    )

    top_rows = (
        db.query(
            Product.sku,
            Product.name,
            func.sum(SalesTransaction.quantity * SalesTransaction.unit_price).label("revenue"),
        )
        .join(SalesTransaction, SalesTransaction.product_id == Product.id)
        .filter(Product.organization_id == org_id)
        .group_by(Product.id)
        .order_by(func.sum(SalesTransaction.quantity * SalesTransaction.unit_price).desc())
        .limit(10)
        .all()
    )

    return {
        "total_revenue": round(total_revenue, 2),
        "avg_daily_revenue": round(avg_daily, 2),
        "trend_pct": trend_pct,
        "days_of_history": int(len(series)),
        "top_products": [
            {"sku": r.sku, "name": r.name, "revenue": round(float(r.revenue), 2)} for r in top_rows
        ],
    }


def run_company_forecast(db: Session, org_id: int, horizon_days: int = 14) -> ForecastResult:
    series = daily_revenue_series(db, org_id)
    if len(series) < 30:
        raise ValueError("Need at least 30 days of sales history to forecast reliably")

    outcome: ForecastOutcome = forecast_daily_series(series, horizon_days=horizon_days)

    result = ForecastResult(
        organization_id=org_id,
        scope="company",
        model_name=outcome.model_name,
        horizon_days=outcome.horizon_days,
        mae=outcome.mae,
        rmse=outcome.rmse,
        mape=outcome.mape,
        forecast_points=outcome.points + outcome.future_points,
    )
    db.add(result)
    db.commit()
    db.refresh(result)
    return result
