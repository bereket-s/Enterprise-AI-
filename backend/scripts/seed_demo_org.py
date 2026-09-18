"""End-to-end pipeline run: create a demo organization, ingest every public dataset,
train/score every module, and dump the resulting metrics to report/chapter4_results.json.

This is both an integration smoke test (if this script runs clean, the whole vertical
slice works) and the source of the real numbers used in the MSc report's Results chapter.

Run:  python backend/scripts/seed_demo_org.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

import pandas as pd  # noqa: E402

from app.core.database import Base, SessionLocal, engine  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.core.modules import MODULE_REGISTRY  # noqa: E402
from app.models.organization import ModuleEnablement, Organization  # noqa: E402
from app.models.user import RoleEnum, User  # noqa: E402
from app.services import bi_service, fraud_service, inventory_service, maintenance_service, workforce_service  # noqa: E402

DATA_DIR = BACKEND_DIR.parent / "data" / "raw"
REPORT_DIR = BACKEND_DIR.parent / "report"
REPORT_DIR.mkdir(exist_ok=True)

ONLINE_RETAIL_COLUMN_MAP = {
    "StockCode": "product_id",
    "Description": "product_name",
    "Quantity": "quantity",
    "InvoiceDate": "transaction_date",
    "UnitPrice": "unit_price",
    "CustomerID": "customer_ref",
    "Country": "country",
}


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def get_or_create_demo_org(db) -> Organization:
    org = db.query(Organization).filter(Organization.name == "Demo Retail & Services Co").first()
    if org:
        return org
    org = Organization(name="Demo Retail & Services Co", industry="retail", size="201-500", country="United Kingdom")
    db.add(org)
    db.flush()
    for module in MODULE_REGISTRY:
        db.add(ModuleEnablement(organization_id=org.id, module_key=module.key, enabled=True))
    if not db.query(User).filter(User.email == "admin@demo.local").first():
        db.add(
            User(
                organization_id=org.id,
                email="admin@demo.local",
                hashed_password=hash_password("DemoPassword123!"),
                full_name="Demo Admin",
                role=RoleEnum.org_admin,
            )
        )
    db.commit()
    return org


def run() -> dict:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    results: dict = {}

    org = get_or_create_demo_org(db)
    log(f"Organization ready: id={org.id}")

    # ---- BI & Forecasting -------------------------------------------------
    log("Ingesting Online Retail sales data...")
    df = pd.read_csv(DATA_DIR / "online_retail.csv")
    df = df.rename(columns=ONLINE_RETAIL_COLUMN_MAP)
    ingest_result = bi_service.ingest_sales_dataframe(db, org.id, df)
    log(f"  {ingest_result}")
    results["bi_ingest"] = ingest_result

    log("Running company revenue forecast...")
    forecast = bi_service.run_company_forecast(db, org.id, horizon_days=14)
    results["bi_forecast"] = {"mae": forecast.mae, "rmse": forecast.rmse, "mape": forecast.mape, "model": forecast.model_name}
    log(f"  {results['bi_forecast']}")

    results["bi_kpis"] = bi_service.compute_kpis(db, org.id)

    # ---- Inventory ----------------------------------------------------------
    log("Generating reorder recommendations...")
    recs = inventory_service.generate_reorder_recommendations(db, org.id)
    risk_counts = pd.Series([r.risk_label for r in recs]).value_counts().to_dict() if recs else {}
    results["inventory"] = {"products_analyzed": len(recs), "risk_distribution": risk_counts}
    log(f"  {results['inventory']}")

    # ---- Fraud ----------------------------------------------------------------
    log("Ingesting fraud transaction sample...")
    fraud_ingest = fraud_service.ingest_fraud_sample(db, org.id, str(DATA_DIR / "creditcard.csv"))
    log(f"  {fraud_ingest}")
    log("Training fraud model...")
    fraud_eval = fraud_service.train_and_score(db, org.id)
    results["fraud"] = {"ingest": fraud_ingest, "metrics": fraud_eval.metrics, "train_rows": fraud_eval.train_rows, "test_rows": fraud_eval.test_rows}
    log(f"  {results['fraud']['metrics']}")

    # ---- Predictive Maintenance -------------------------------------------
    log("Ingesting equipment sensor sample...")
    maint_ingest = maintenance_service.ingest_equipment_sample(db, org.id, str(DATA_DIR / "ai4i2020.csv"))
    log(f"  {maint_ingest}")
    log("Training maintenance model...")
    maint_eval = maintenance_service.train_and_score(db, org.id)
    results["maintenance"] = {"ingest": maint_ingest, "metrics": maint_eval.metrics, "train_rows": maint_eval.train_rows, "test_rows": maint_eval.test_rows}
    log(f"  {results['maintenance']['metrics']}")

    # ---- Workforce ------------------------------------------------------------
    log("Ingesting employee data...")
    emp_ingest = workforce_service.ingest_employees(db, org.id, str(DATA_DIR / "employee_attrition.csv"))
    log(f"  {emp_ingest}")
    log("Computing performance scores...")
    scores = workforce_service.compute_performance_scores(db, org.id)
    score_values = [s.score for s in scores]
    log("Training attrition model...")
    attrition_eval = workforce_service.train_attrition_and_score(db, org.id)
    results["workforce"] = {
        "ingest": emp_ingest,
        "performance_score_mean": round(sum(score_values) / len(score_values), 1) if score_values else 0,
        "attrition_metrics": attrition_eval.metrics,
        "train_rows": attrition_eval.train_rows,
        "test_rows": attrition_eval.test_rows,
    }
    log(f"  {results['workforce']['attrition_metrics']}")

    db.close()
    return results


if __name__ == "__main__":
    started = time.time()
    output = run()
    output["_elapsed_seconds"] = round(time.time() - started, 1)
    out_path = REPORT_DIR / "chapter4_results.json"
    out_path.write_text(json.dumps(output, indent=2, default=str))
    log(f"Done in {output['_elapsed_seconds']}s. Results written to {out_path}")
