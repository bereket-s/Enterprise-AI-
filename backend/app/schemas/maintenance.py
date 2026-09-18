from pydantic import BaseModel, ConfigDict


class EquipmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    external_ref: str
    machine_type: str
    failure_risk_score: float
    risk_label: str
    contributing_factors: list[str]
