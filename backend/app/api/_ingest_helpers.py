"""Shared file-upload preview/commit helpers (#1) for every module's router —
factored out so BI, Fraud, Maintenance, and Workforce all expose the same
two-step "preview the mapping, then confirm it" upload flow without
duplicating the CSV-parsing/mapping glue four times.
"""
from __future__ import annotations

import io
import json

import pandas as pd
from fastapi import HTTPException, UploadFile, status

from app.services import integration_pipeline


def read_csv(file: UploadFile) -> pd.DataFrame:
    content = file.file.read()
    try:
        return pd.read_csv(io.BytesIO(content))
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Could not parse CSV: {exc}") from exc


def preview(module_key: str, file: UploadFile) -> dict:
    df = read_csv(file)
    mapping = integration_pipeline.preview_mapping(module_key, df)
    return {
        "columns": list(df.columns),
        "suggested_mapping": mapping,
        "sample_rows": df.head(5).fillna("").to_dict(orient="records"),
    }


def commit(module_key: str, db, org_id: int, file: UploadFile, mapping_json: str) -> dict:
    df = read_csv(file)
    try:
        field_map = json.loads(mapping_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "mapping must be a JSON object") from exc
    try:
        return integration_pipeline.ingest_with_mapping(db, org_id, module_key, df, field_map)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
