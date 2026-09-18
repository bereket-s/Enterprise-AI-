from datetime import datetime

from pydantic import BaseModel, ConfigDict


class FraudTransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    external_ref: str
    amount: float
    occurred_at: datetime
    risk_score: float
    risk_label: str
    reason_codes: list[str]
    status: str


class StatusUpdateRequest(BaseModel):
    status: str  # investigating | approved | blocked


class EvaluationOut(BaseModel):
    model_config = ConfigDict(protected_namespaces=(), from_attributes=True)

    id: int
    model_name: str
    metrics: dict
    train_rows: int
    test_rows: int
