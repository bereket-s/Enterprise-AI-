from datetime import datetime

from pydantic import BaseModel, ConfigDict


class GenericIngestResult(BaseModel):
    """Response for the Fraud/Maintenance/Workforce ingest/commit endpoints —
    kept separate from BI's IngestResult since "products ingested" has no
    meaning outside the BI module."""

    records_ingested: int


class ApiKeyCreate(BaseModel):
    name: str


class ApiKeyCreated(BaseModel):
    id: int
    name: str
    key_prefix: str
    raw_key: str  # shown exactly once, at creation time


class ApiKeyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    key_prefix: str
    created_at: datetime
    last_used_at: datetime | None
    revoked: bool


class DatabaseConnectionCreate(BaseModel):
    module_key: str
    name: str
    dialect: str
    host: str
    port: int
    database_name: str
    username: str
    password: str
    source_query: str


class DatabaseConnectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    module_key: str
    name: str
    dialect: str
    host: str
    port: int
    database_name: str
    username: str
    source_query: str
    created_at: datetime
    last_synced_at: datetime | None
    last_status: str | None


class ScheduledJobCreate(BaseModel):
    module_key: str
    job_type: str  # data_sync | retrain
    connection_id: int | None = None
    interval_minutes: int = 1440


class ScheduledJobUpdate(BaseModel):
    enabled: bool | None = None
    interval_minutes: int | None = None


class ScheduledJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    module_key: str
    job_type: str
    connection_id: int | None
    interval_minutes: int
    enabled: bool
    last_run_at: datetime | None
    last_status: str | None


class WebhookCreate(BaseModel):
    module_key: str


class WebhookCreated(BaseModel):
    id: int
    module_key: str
    url_path: str
    secret: str  # shown exactly once, at creation time


class WebhookOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    module_key: str
    token: str
    created_at: datetime
    last_received_at: datetime | None
    receive_count: int


class ConnectorCatalogEntry(BaseModel):
    connector_type: str
    display_name: str
    modules: list[str]
    description: str
    status: str


class ConnectorCreate(BaseModel):
    connector_type: str
    module_key: str
    name: str


class ConnectorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    connector_type: str
    module_key: str
    name: str
    status: str
    created_at: datetime
    last_synced_at: datetime | None


class PushRequest(BaseModel):
    records: list[dict]


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int | None
    action: str
    detail: dict
    created_at: datetime


class UsageMetricOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    module_key: str
    day: str
    request_count: int
