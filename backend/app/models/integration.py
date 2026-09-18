"""Data models backing all six integration paths.

  1. File upload           -> no dedicated model; handled inline per module router.
  2. Database connector     -> DatabaseConnection
  3. REST API push          -> ApiKey (auth) + the module's own ingestion endpoint
  4. Scheduled sync         -> ScheduledJob (job_type="data_sync"), driven by app/core/scheduler.py
  5. Webhooks               -> WebhookEndpoint
  6. Pre-built connectors   -> ConnectorInstance

ScheduledJob also covers scheduled *retraining* (job_type="retrain"), which is the
"scheduled retraining" piece of the model-registry gap in docs/architecture.md §10.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TenantMixin, utcnow


class ApiKey(Base, TenantMixin):
    """Machine-to-machine credential for REST push (#3) and connectors (#6) —
    deliberately separate from user JWTs so a company's integration doesn't need
    a human's login session, and can be revoked without affecting any user."""

    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    key_prefix: Mapped[str] = mapped_column(String(12))  # shown in UI, e.g. "eak_3f9a2b1c"
    key_hash: Mapped[str] = mapped_column(String(128))  # sha256 of the full key; the raw key is never stored
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)


class DatabaseConnection(Base, TenantMixin):
    """A company's own database, connected read-only (#2). Password is encrypted
    at rest (app/core/crypto.py) and never returned by any API response."""

    __tablename__ = "database_connections"

    id: Mapped[int] = mapped_column(primary_key=True)
    module_key: Mapped[str] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(200))
    dialect: Mapped[str] = mapped_column(String(20))  # postgresql | mysql | mssql | oracle | sqlite
    host: Mapped[str] = mapped_column(String(255))
    port: Mapped[int] = mapped_column(Integer)
    database_name: Mapped[str] = mapped_column(String(200))
    username: Mapped[str] = mapped_column(String(200))
    encrypted_password: Mapped[str] = mapped_column(String(500))
    source_query: Mapped[str] = mapped_column(String(2000))  # a table name or a SELECT statement
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_status: Mapped[str | None] = mapped_column(String(500), nullable=True)


class ScheduledJob(Base, TenantMixin):
    """Recurring background work (#4): either a data sync against a
    DatabaseConnection, or a scheduled model retrain for a module."""

    __tablename__ = "scheduled_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    module_key: Mapped[str] = mapped_column(String(50))
    job_type: Mapped[str] = mapped_column(String(20))  # "data_sync" | "retrain"
    connection_id: Mapped[int | None] = mapped_column(ForeignKey("database_connections.id"), nullable=True)
    interval_minutes: Mapped[int] = mapped_column(Integer, default=1440)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_status: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    connection: Mapped["DatabaseConnection"] = relationship()


class WebhookEndpoint(Base, TenantMixin):
    """A unique, per-module inbound URL (#5). The company's system POSTs one record
    at a time here the moment something happens, signed with an HMAC secret so the
    platform can verify the sender without a login session."""

    __tablename__ = "webhook_endpoints"

    id: Mapped[int] = mapped_column(primary_key=True)
    module_key: Mapped[str] = mapped_column(String(50))
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)  # part of the public URL
    encrypted_secret: Mapped[str] = mapped_column(String(500))  # HMAC signing secret, encrypted at rest
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    last_received_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    receive_count: Mapped[int] = mapped_column(Integer, default=0)


class ConnectorInstance(Base, TenantMixin):
    """A named, pre-built connector (#6) — Salesforce/QuickBooks/SAP-style adapters.

    Without real OAuth app credentials for these third parties, `status` is always
    "simulated": the adapter runs its full mapping/ingestion pipeline against
    representative sample data shaped like that system's real export, so the
    integration *pattern* is genuinely exercised end-to-end even though no live
    account is reachable. Swapping in real OAuth credentials later only changes how
    the adapter fetches rows — everything downstream is unchanged.
    """

    __tablename__ = "connector_instances"

    id: Mapped[int] = mapped_column(primary_key=True)
    module_key: Mapped[str] = mapped_column(String(50))
    connector_type: Mapped[str] = mapped_column(String(50))  # salesforce | quickbooks | sap | generic_rest
    name: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20), default="simulated")  # simulated | connected
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
