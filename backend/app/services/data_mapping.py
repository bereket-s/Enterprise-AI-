"""Auto column-mapping: match an uploaded file's headers to a module's canonical schema.

This is the "automatic data mapping" feature from the platform design — a company
uploads a CSV with whatever column names it already uses (product_id, sku, ItemCode...)
and the platform proposes a mapping to canonical fields for the admin to confirm,
instead of requiring the file to match an exact template.
"""
from __future__ import annotations

import difflib
import re

SYNONYMS: dict[str, list[str]] = {
    "product_id": [
        "sku", "stockcode", "stock_code", "item_code", "itemcode", "product_code",
        "opportunity_product__c", "itemref", "matnr",
    ],
    "product_name": ["description", "item_name", "itemname", "name", "itemdescription", "maktx"],
    "quantity": ["qty", "quantity_sold", "units", "unitssold"],
    "unit_price": ["price", "unitprice", "sale_price", "saleprice", "unit_price__c", "rate"],
    "transaction_date": ["invoicedate", "date", "sale_date", "saledate", "order_date", "close_date", "txndate"],
    "customer_ref": ["customerid", "customer_id", "custid", "account_id", "customerref"],
    "country": ["region", "market"],
    "employee_id": ["empid", "emp_id", "employeeid", "staff_id"],
    "department": ["dept", "division", "department__c"],
    "current_stock": ["stock", "inventory", "on_hand", "onhand", "stock_level", "labst", "qtyonhand"],
    "supplier_lead_time_days": ["lead_time", "leadtime", "lead_time_days"],
    # Fraud (bring-your-own-data)
    "transaction_ref": ["transaction_id", "txn_id", "reference", "trans_id"],
    "amount": ["amt", "value", "transaction_amount"],
    "timestamp": ["date", "datetime", "transaction_date", "trans_date_trans_time", "occurred_at"],
    "account_ref": ["cc_num", "card_number", "customer_id", "account_id", "account_number"],
    "merchant": ["merchant_name", "vendor", "payee"],
    "category": ["merchant_category", "transaction_category", "type"],
    "customer_lat": ["lat", "latitude", "home_lat"],
    "customer_long": ["long", "lng", "longitude", "home_long"],
    "merchant_lat": ["merch_lat", "merchant_latitude"],
    "merchant_long": ["merch_long", "merchant_longitude"],
    "is_fraud": ["fraud", "fraud_flag", "is_fraudulent", "label"],
    # Predictive Maintenance (bring-your-own-data)
    "equipment_ref": ["equipment_id", "machine_id", "asset_id", "product_id_sensor", "device_id", "equnr"],
    "machine_type": ["type", "equipment_type", "asset_type", "bautl"],
    "temperature": ["temp", "air_temperature", "process_temperature", "temp_reading"],
    "vibration": ["vibration_level", "vib"],
    "pressure": ["pressure_level", "psi"],
    "rotational_speed": ["rpm", "speed", "rotational_speed_rpm"],
    "torque": ["torque_nm", "torque_reading"],
    "tool_wear": ["tool_wear_min", "wear", "wear_min"],
    "failure": ["machine_failure", "failed", "breakdown"],
    # Workforce (bring-your-own-data)
    "employee_ref": ["employee_id", "emp_id", "staff_id", "worker_id", "employee_id__c"],
    "job_role": ["role", "position", "title"],
    "job_satisfaction": ["satisfaction", "job_sat", "satisfaction_score__c"],
    "environment_satisfaction": ["env_satisfaction", "workplace_satisfaction"],
    "job_involvement": ["involvement", "engagement"],
    "years_since_last_promotion": ["last_promotion", "years_since_promotion"],
    "years_at_company": ["tenure", "years_employed", "seniority", "tenure_years__c"],
    "monthly_income": ["salary", "income", "monthly_salary"],
    "attrition": ["attrition_flag", "left_company", "resigned", "churned"],
}


def _normalize(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.strip().lower())


def suggest_mapping(source_columns: list[str], canonical_fields: list[str]) -> dict[str, str | None]:
    """Return {canonical_field: best_matching_source_column_or_None}.

    A source column, once claimed by one canonical field, is removed from
    consideration for the rest — otherwise e.g. a "merchant" column can look
    like a close fuzzy-match for the unrelated "merchant_lat"/"merchant_long"
    fields (they share the long "merchant" prefix) and get double-mapped onto
    a column holding the wrong kind of data entirely.
    """
    normalized_source = {_normalize(c): c for c in source_columns}
    mapping: dict[str, str | None] = {}

    for field in canonical_fields:
        candidates = [_normalize(field)] + [_normalize(s) for s in SYNONYMS.get(field, [])]
        match = None
        for candidate in candidates:
            if candidate in normalized_source:
                match = normalized_source[candidate]
                break
        if match is None:
            close = difflib.get_close_matches(_normalize(field), normalized_source.keys(), n=1, cutoff=0.75)
            if close:
                match = normalized_source[close[0]]
        mapping[field] = match
        if match is not None:
            del normalized_source[_normalize(match)]

    return mapping
