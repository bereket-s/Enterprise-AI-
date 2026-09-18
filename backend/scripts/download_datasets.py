"""
Download and cache the public datasets that back each platform module.

Run:  python backend/scripts/download_datasets.py

Sources (all freely downloadable, no auth required):
  - Online Retail II (UCI ML Repository)        -> BI/Forecasting + Inventory modules
  - AI4I 2020 Predictive Maintenance (UCI)       -> Predictive Maintenance module
  - Credit Card Fraud Detection (HF mirror)      -> Fraud & Anomaly Detection module
  - IBM-style Employee Attrition (HF mirror)     -> Workforce Intelligence module
"""
from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pandas as pd
import requests

RAW_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

TIMEOUT = 60


def _get(url: str) -> bytes:
    resp = requests.get(url, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.content


def download_online_retail() -> Path:
    out = RAW_DIR / "online_retail.csv"
    if out.exists():
        print(f"[skip] {out.name} already present")
        return out
    print("Downloading Online Retail (UCI)...")
    content = _get("https://archive.ics.uci.edu/static/public/352/online+retail.zip")
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        xlsx_name = next(n for n in zf.namelist() if n.lower().endswith(".xlsx"))
        with zf.open(xlsx_name) as f:
            df = pd.read_excel(f)
    df.to_csv(out, index=False)
    print(f"[ok] saved {out} ({len(df):,} rows)")
    return out


def download_ai4i2020() -> Path:
    out = RAW_DIR / "ai4i2020.csv"
    if out.exists():
        print(f"[skip] {out.name} already present")
        return out
    print("Downloading AI4I 2020 Predictive Maintenance (UCI)...")
    content = _get(
        "https://archive.ics.uci.edu/static/public/601/ai4i+2020+predictive+maintenance+dataset.zip"
    )
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        csv_name = next(n for n in zf.namelist() if n.lower().endswith(".csv"))
        with zf.open(csv_name) as f:
            df = pd.read_csv(f)
    df.to_csv(out, index=False)
    print(f"[ok] saved {out} ({len(df):,} rows)")
    return out


FRAUD_COLUMNS = [
    "trans_date_trans_time", "unix_time", "cc_num", "merchant", "category", "amt",
    "city", "state", "lat", "long", "merch_lat", "merch_long", "is_fraud",
]


def download_credit_card_fraud(n_legit_sample: int = 60_000, seed: int = 42) -> Path:
    """The source mirror is a ~1M-row / 270MB simulated transactions dataset (Sparkov
    generator) with real fields (merchant, category, amount, lat/long) rather than the
    classic PCA-anonymised creditcard.csv. We keep a stratified sample (all fraud rows +
    a random legit sample, ~9% fraud rate) both to keep the repo lightweight and because
    the full file is unnecessary for a capstone-scale training/evaluation run.
    """
    out = RAW_DIR / "creditcard.csv"
    if out.exists():
        print(f"[skip] {out.name} already present")
        return out
    print("Downloading Credit Card Fraud dataset (HuggingFace mirror)... this is ~150MB")
    url = (
        "https://huggingface.co/datasets/dazzle-nu/CIS435-CreditCardFraudDetection/"
        "resolve/refs%2Fconvert%2Fparquet/default/train/0000.parquet"
    )
    df = pd.read_parquet(url, columns=FRAUD_COLUMNS)
    fraud = df[df["is_fraud"] == 1]
    legit = df[df["is_fraud"] == 0].sample(n=n_legit_sample, random_state=seed)
    sample = pd.concat([fraud, legit]).sample(frac=1, random_state=seed).reset_index(drop=True)
    sample.to_csv(out, index=False)
    print(f"[ok] saved {out} ({len(sample):,} rows, fraud rate {sample['is_fraud'].mean():.3f})")
    return out


# The HF mirror pre-encodes categoricals to integers with no label file. Cardinalities
# and per-code frequencies match the well-known IBM Watson HR Attrition dataset almost
# exactly (e.g. Department: 60/898/412 rows -> HR/R&D/Sales, attrition rate ~15.8% vs the
# original's ~16.1%), consistent with a plain alphabetical LabelEncoder over the original
# category names. Decoded here so the platform can show real department/role names.
DEPARTMENT_MAP = {0: "Human Resources", 1: "Research & Development", 2: "Sales"}
BUSINESS_TRAVEL_MAP = {0: "Non-Travel", 1: "Travel_Frequently", 2: "Travel_Rarely"}
MARITAL_STATUS_MAP = {0: "Divorced", 1: "Married", 2: "Single"}
JOB_ROLE_MAP = {
    0: "Healthcare Representative", 1: "Human Resources", 2: "Laboratory Technician",
    3: "Manager", 4: "Manufacturing Director", 5: "Research Director",
    6: "Research Scientist", 7: "Sales Executive", 8: "Sales Representative",
}


def download_employee_attrition() -> Path:
    out = RAW_DIR / "employee_attrition.csv"
    if out.exists():
        print(f"[skip] {out.name} already present")
        return out
    print("Downloading Employee Attrition dataset (HuggingFace mirror)...")
    train_url = (
        "https://huggingface.co/datasets/eduvance/employee_attrition/"
        "resolve/refs%2Fconvert%2Fparquet/default/train/0000.parquet"
    )
    test_url = (
        "https://huggingface.co/datasets/eduvance/employee_attrition/"
        "resolve/refs%2Fconvert%2Fparquet/default/test/0000.parquet"
    )
    df = pd.concat([pd.read_parquet(train_url), pd.read_parquet(test_url)], ignore_index=True)

    df["Department"] = df["Department_Num"].map(DEPARTMENT_MAP)
    df["BusinessTravel"] = df["BusinessTravel_Num"].map(BUSINESS_TRAVEL_MAP)
    df["MaritalStatus"] = df["MaritalStatus_Num"].map(MARITAL_STATUS_MAP)
    df["JobRole"] = df["JobRole_Num"].map(JOB_ROLE_MAP)
    df["Attrition"] = df["Attrition_Num"].map({0: "No", 1: "Yes"})
    df = df.drop(columns=["Department_Num", "BusinessTravel_Num", "MaritalStatus_Num", "JobRole_Num", "Attrition_Num"])
    df.insert(0, "EmployeeNumber", range(1, len(df) + 1))

    df.to_csv(out, index=False)
    print(f"[ok] saved {out} ({len(df):,} rows)")
    return out


if __name__ == "__main__":
    download_online_retail()
    download_ai4i2020()
    download_credit_card_fraud()
    download_employee_attrition()
    print("\nAll datasets ready in", RAW_DIR)
