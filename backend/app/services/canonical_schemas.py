"""Canonical field lists per module for the "bring your own data" ingestion path.

Every integration method (file upload, DB connector, REST push, scheduled sync,
webhook, pre-built connector) ultimately produces a DataFrame with these column
names — suggest_mapping() (data_mapping.py) gets an arbitrary company's own column
names there, and the generic ingestion/training functions (generic_ingest.py,
generic_classifier.py) only ever see the canonical names, so a new integration
transport doesn't require touching either of those layers.
"""
from __future__ import annotations

# (all_fields, required_fields) per module.
FRAUD_FIELDS = (
    ["transaction_ref", "amount", "timestamp", "account_ref", "merchant", "category",
     "customer_lat", "customer_long", "merchant_lat", "merchant_long", "is_fraud"],
    ["amount", "timestamp", "account_ref"],
)

MAINTENANCE_FIELDS = (
    ["equipment_ref", "machine_type", "temperature", "vibration", "pressure",
     "rotational_speed", "torque", "tool_wear", "failure"],
    ["equipment_ref"],
)
# At least one of these sensor readings must be present, on top of the required fields above.
MAINTENANCE_SENSOR_FIELDS = ["temperature", "vibration", "pressure", "rotational_speed", "torque", "tool_wear"]

WORKFORCE_FIELDS = (
    ["employee_ref", "department", "job_role", "age", "monthly_income", "years_at_company",
     "job_satisfaction", "environment_satisfaction", "job_involvement",
     "years_since_last_promotion", "attrition"],
    ["employee_ref", "department"],
)

INVENTORY_FIELDS = (
    ["product_id", "product_name", "current_stock", "supplier_lead_time_days"],
    ["product_id", "current_stock"],
)


def missing_required(field_map: dict[str, str | None], required: list[str]) -> list[str]:
    return [f for f in required if not field_map.get(f)]
