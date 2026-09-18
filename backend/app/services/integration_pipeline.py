"""The single door every integration path funnels through after this point:
given a DataFrame in *whatever* column names the source system used, resolve it
to canonical fields and hand it to the right module's ingestion function.

File upload (#1) uses preview()/ingest_with_mapping() directly so a human can
confirm the mapping first. DB sync (#2), scheduled sync (#4), webhooks (#5), and
connectors (#6) have no human in the loop, so auto_ingest() applies
suggest_mapping()'s best guess automatically — the same auto-mapping logic, just
without a confirmation click.
"""
from __future__ import annotations

import pandas as pd

from app.services import bi_service, fraud_service, inventory_service, maintenance_service, workforce_service
from app.services.canonical_schemas import (
    FRAUD_FIELDS,
    INVENTORY_FIELDS,
    MAINTENANCE_FIELDS,
    WORKFORCE_FIELDS,
    missing_required,
)
from app.services.data_mapping import suggest_mapping

BI_FIELDS = (bi_service.CANONICAL_FIELDS, ["product_id", "quantity", "unit_price", "transaction_date"])

MODULE_SCHEMAS: dict[str, tuple[list[str], list[str]]] = {
    "bi_forecasting": BI_FIELDS,
    "fraud": FRAUD_FIELDS,
    "maintenance": MAINTENANCE_FIELDS,
    "workforce": WORKFORCE_FIELDS,
    "inventory": INVENTORY_FIELDS,
}

MODULE_INGEST_FUNCS = {
    "bi_forecasting": bi_service.ingest_sales_dataframe,
    "fraud": fraud_service.ingest_fraud_generic,
    "maintenance": maintenance_service.ingest_equipment_generic,
    "workforce": workforce_service.ingest_employees_generic,
    "inventory": inventory_service.ingest_inventory_generic,
}


def preview_mapping(module_key: str, df: pd.DataFrame) -> dict[str, str | None]:
    fields, _required = MODULE_SCHEMAS[module_key]
    return suggest_mapping(list(df.columns), fields)


def ingest_with_mapping(db, org_id: int, module_key: str, df: pd.DataFrame, field_map: dict[str, str]) -> dict:
    _fields, required = MODULE_SCHEMAS[module_key]
    missing = missing_required(field_map, required)
    if missing:
        raise ValueError(f"Missing required mapping for: {missing}")
    renamed = df.rename(columns={source: canonical for canonical, source in field_map.items() if source})
    return MODULE_INGEST_FUNCS[module_key](db, org_id, renamed)


def auto_ingest(db, org_id: int, module_key: str, df: pd.DataFrame) -> dict:
    """No human confirmation step — used by DB sync, scheduled sync, webhooks, and
    connectors, all of which have no admin present to click 'confirm mapping'."""
    mapping = preview_mapping(module_key, df)
    return ingest_with_mapping(db, org_id, module_key, df, mapping)
