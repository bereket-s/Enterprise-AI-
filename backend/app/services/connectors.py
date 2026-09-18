"""Pre-built connector adapters (#6 of the six integration paths).

No real OAuth credentials exist for Salesforce/QuickBooks/SAP in this environment,
so each adapter runs in "simulated" mode: it generates a small batch of rows shaped
exactly like that system's real export for the chosen module (Salesforce's object
field names, QuickBooks' report columns, SAP's field codes), then puts it through
suggest_mapping() and the *same* generic ingestion functions a real pulled batch
would use. The only thing that's fake is where the rows come from — the mapping,
validation, storage, and training pipeline downstream is completely real and is the
same code a live OAuth-backed version of this adapter would call.

Swapping in a real connection later means replacing `_simulated_rows()` with an
actual API/OAuth client call — nothing else in this file or downstream changes.
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

import pandas as pd

CATALOG = [
    {
        "connector_type": "salesforce",
        "display_name": "Salesforce",
        "modules": ["bi_forecasting", "workforce"],
        "description": "Pulls Opportunity records (as sales) or Employee/User records (as workforce data).",
        "status": "simulated",
    },
    {
        "connector_type": "quickbooks",
        "display_name": "QuickBooks",
        "modules": ["bi_forecasting", "inventory"],
        "description": "Pulls Sales Receipts and Item/Inventory reports.",
        "status": "simulated",
    },
    {
        "connector_type": "sap",
        "display_name": "SAP",
        "modules": ["maintenance", "inventory"],
        "description": "Pulls Plant Maintenance equipment records and Materials Management inventory.",
        "status": "simulated",
    },
    {
        "connector_type": "generic_rest",
        "display_name": "Generic REST API",
        "modules": ["bi_forecasting", "fraud", "maintenance", "workforce"],
        "description": "For any system with its own REST API — point it at your endpoint (same auth as #3).",
        "status": "simulated",
    },
]


def _simulated_salesforce_rows(module_key: str, seed: int) -> pd.DataFrame:
    rng = random.Random(seed)
    if module_key == "workforce":
        depts = ["Sales", "Human Resources", "Research & Development"]
        return pd.DataFrame(
            [
                {
                    "Employee_ID__c": f"SF-{1000+i}",
                    "Department__c": rng.choice(depts),
                    "Title": rng.choice(["Account Executive", "Recruiter", "Engineer"]),
                    "Tenure_Years__c": round(rng.uniform(0, 12), 1),
                    "Satisfaction_Score__c": rng.randint(1, 4),
                }
                for i in range(30)
            ]
        )
    # bi_forecasting: Opportunity records as sales
    base = datetime.now(timezone.utc) - timedelta(days=60)
    return pd.DataFrame(
        [
            {
                "Opportunity_Product__c": rng.choice(["Widget A", "Widget B", "Service Plan"]),
                "Quantity": rng.randint(1, 20),
                "Unit_Price__c": round(rng.uniform(10, 500), 2),
                "Close_Date": (base + timedelta(days=rng.randint(0, 60))).date().isoformat(),
                "Account_Id": f"ACC-{rng.randint(1, 40)}",
            }
            for _ in range(150)
        ]
    )


def _simulated_quickbooks_rows(module_key: str, seed: int) -> pd.DataFrame:
    rng = random.Random(seed)
    base = datetime.now(timezone.utc) - timedelta(days=60)
    return pd.DataFrame(
        [
            {
                "ItemRef": rng.choice(["SKU-100", "SKU-200", "SKU-300"]),
                "ItemDescription": rng.choice(["Blue Widget", "Red Widget", "Service Hour"]),
                "Qty": rng.randint(1, 15),
                "Rate": round(rng.uniform(5, 300), 2),
                "TxnDate": (base + timedelta(days=rng.randint(0, 60))).date().isoformat(),
                "CustomerRef": f"CUST-{rng.randint(1, 25)}",
            }
            for _ in range(150)
        ]
    )


def _simulated_sap_rows(module_key: str, seed: int) -> pd.DataFrame:
    rng = random.Random(seed)
    if module_key == "maintenance":
        return pd.DataFrame(
            [
                {
                    "EQUNR": f"SAP-EQ-{2000+i}",
                    "BAUTL": rng.choice(["L", "M", "H"]),
                    "TEMP_READING": round(rng.uniform(295, 310), 1),
                    "TORQUE_READING": round(rng.uniform(20, 70), 1),
                    "WEAR_MIN": round(rng.uniform(0, 220), 1),
                }
                for i in range(40)
            ]
        )
    # inventory-style materials management extract
    return pd.DataFrame(
        [
            {
                "MATNR": f"MAT-{5000+i}",
                "MAKTX": rng.choice(["Steel Bracket", "Circuit Board", "Casing"]),
                "LABST": rng.randint(0, 500),
            }
            for i in range(40)
        ]
    )


_SIMULATORS = {
    "salesforce": _simulated_salesforce_rows,
    "quickbooks": _simulated_quickbooks_rows,
    "sap": _simulated_sap_rows,
}


def generate_sample_batch(connector_type: str, module_key: str, seed: int = 42) -> pd.DataFrame:
    simulator = _SIMULATORS.get(connector_type)
    if simulator is None:
        raise ValueError(f"No simulator available for connector '{connector_type}'")
    return simulator(module_key, seed)
