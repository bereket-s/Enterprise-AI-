"""Inventory & Procurement Optimization.

Reuses the Product/SalesTransaction data ingested by the BI module (the platform's
"common data layer" idea) rather than requiring a second upload. Current stock levels
aren't present in the public Online Retail dataset, so they are synthesised from each
product's recent demand the first time a snapshot is generated — this assumption is
called out explicitly in the report as a limitation of using public data without a
live ERP feed.
"""
from __future__ import annotations

import random
from datetime import date, timedelta

import numpy as np
import pandas as pd
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.bi import Product, SalesTransaction
from app.models.inventory import InventorySnapshot, ReorderRecommendation
from app.models.base import utcnow

Z_SCORE_95 = 1.65
DEFAULT_LEAD_TIME_DAYS = 14

CANONICAL_FIELDS = ["product_id", "product_name", "current_stock", "supplier_lead_time_days"]


def ingest_inventory_generic(db: Session, org_id: int, df: pd.DataFrame) -> dict:
    """Bring-your-own current stock levels (one of the six integration paths).

    This replaces the synthesised stock figure described in the module docstring
    above with a company's real on-hand quantities: each row is upserted onto the
    existing product (created if new, matched by SKU) as its latest InventorySnapshot,
    rather than always deriving stock from demand history.
    """
    df = df.dropna(subset=["product_id", "current_stock"]).copy()
    df["current_stock"] = pd.to_numeric(df["current_stock"], errors="coerce")
    df = df.dropna(subset=["current_stock"])

    existing_products = {
        p.sku: p for p in db.query(Product).filter(Product.organization_id == org_id).all()
    }
    for sku, group in df.groupby("product_id"):
        sku = str(sku)
        if sku not in existing_products:
            name = sku
            if "product_name" in group.columns and pd.notna(group["product_name"].iloc[0]):
                name = str(group["product_name"].iloc[0])
            product = Product(organization_id=org_id, sku=sku, name=name[:255])
            db.add(product)
            db.flush()
            existing_products[sku] = product

    existing_snapshots = {
        s.product_id: s
        for s in db.query(InventorySnapshot).filter(InventorySnapshot.organization_id == org_id).all()
    }

    created = 0
    updated = 0
    for record in df.itertuples(index=False):
        product = existing_products[str(record.product_id)]
        lead_time_raw = getattr(record, "supplier_lead_time_days", None)
        lead_time = (
            int(lead_time_raw) if lead_time_raw is not None and not pd.isna(lead_time_raw) else None
        )
        snapshot = existing_snapshots.get(product.id)
        if snapshot is None:
            snapshot = InventorySnapshot(
                organization_id=org_id,
                product_id=product.id,
                current_stock=int(record.current_stock),
                supplier_lead_time_days=lead_time or DEFAULT_LEAD_TIME_DAYS,
            )
            db.add(snapshot)
            existing_snapshots[product.id] = snapshot
            created += 1
        else:
            snapshot.current_stock = int(record.current_stock)
            if lead_time is not None:
                snapshot.supplier_lead_time_days = lead_time
            snapshot.snapshot_date = utcnow()
            updated += 1

    db.commit()
    return {
        "products": len(existing_products),
        "snapshots_created": created,
        "snapshots_updated": updated,
        "snapshots_ingested": created + updated,
    }


def _product_daily_demand(db: Session, org_id: int, product_id: int) -> pd.Series:
    rows = (
        db.query(SalesTransaction.transaction_date, func.sum(SalesTransaction.quantity))
        .filter(SalesTransaction.organization_id == org_id, SalesTransaction.product_id == product_id)
        .group_by(SalesTransaction.transaction_date)
        .all()
    )
    if not rows:
        return pd.Series(dtype=float)
    df = pd.DataFrame(rows, columns=["date", "qty"])
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date")["qty"].asfreq("D").fillna(0.0)


def ensure_inventory_snapshots(db: Session, org_id: int, top_n: int = 50, seed: int = 42) -> int:
    """Create a synthetic current-stock snapshot for the org's top-N products by volume, if missing."""
    rng = random.Random(seed)

    top_products = (
        db.query(Product.id)
        .join(SalesTransaction, SalesTransaction.product_id == Product.id)
        .filter(Product.organization_id == org_id)
        .group_by(Product.id)
        .order_by(func.sum(SalesTransaction.quantity).desc())
        .limit(top_n)
        .all()
    )
    existing = {
        s.product_id
        for s in db.query(InventorySnapshot).filter(InventorySnapshot.organization_id == org_id).all()
    }

    created = 0
    for (product_id,) in top_products:
        if product_id in existing:
            continue
        demand = _product_daily_demand(db, org_id, product_id)
        avg_daily = float(demand.tail(30).mean()) if not demand.empty else 1.0
        days_of_supply = rng.uniform(5, 25)
        current_stock = max(0, int(avg_daily * days_of_supply))
        db.add(
            InventorySnapshot(
                organization_id=org_id,
                product_id=product_id,
                current_stock=current_stock,
                supplier_lead_time_days=DEFAULT_LEAD_TIME_DAYS,
            )
        )
        created += 1
    db.commit()
    return created


def _risk_label(stockout_probability: float) -> str:
    if stockout_probability >= 0.75:
        return "critical"
    if stockout_probability >= 0.5:
        return "high"
    if stockout_probability >= 0.25:
        return "medium"
    return "low"


def generate_reorder_recommendations(db: Session, org_id: int) -> list[ReorderRecommendation]:
    ensure_inventory_snapshots(db, org_id)

    snapshots = (
        db.query(InventorySnapshot).filter(InventorySnapshot.organization_id == org_id).all()
    )
    results: list[ReorderRecommendation] = []

    for snap in snapshots:
        demand = _product_daily_demand(db, org_id, snap.product_id)
        if demand.empty or len(demand) < 14:
            continue

        recent = demand.tail(60)
        mean_daily = float(recent.mean())
        std_daily = float(recent.std(ddof=0)) or mean_daily * 0.25

        lead_time = snap.supplier_lead_time_days
        expected_demand_lead_time = mean_daily * lead_time
        safety_stock = Z_SCORE_95 * std_daily * (lead_time**0.5)
        reorder_point = expected_demand_lead_time + safety_stock

        deficit = reorder_point - snap.current_stock
        stockout_probability = float(np.clip(deficit / (reorder_point + 1e-6), 0, 1)) if reorder_point > 0 else 0.0
        recommended_qty = max(0.0, deficit + expected_demand_lead_time)

        rec = ReorderRecommendation(
            organization_id=org_id,
            product_id=snap.product_id,
            expected_demand=round(expected_demand_lead_time, 1),
            current_stock=snap.current_stock,
            safety_stock=round(safety_stock, 1),
            reorder_point=round(reorder_point, 1),
            recommended_order_qty=round(recommended_qty, 1),
            stockout_probability=round(stockout_probability, 3),
            risk_label=_risk_label(stockout_probability),
        )
        db.add(rec)
        results.append(rec)

    db.commit()
    for r in results:
        db.refresh(r)
    return results
