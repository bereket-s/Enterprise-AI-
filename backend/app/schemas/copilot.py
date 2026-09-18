from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AskRequest(BaseModel):
    question: str


class ChatLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    question: str
    intent: str
    answer: str
    source_data: dict
    created_at: datetime
