import secrets

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.audit import log_action
from app.core.crypto import encrypt_secret
from app.core.database import get_db
from app.core.deps import current_org_id, get_current_user, hash_api_key, org_id_from_api_key, require_roles
from app.core.webhooks import generate_secret as gen_webhook_secret
from app.core.webhooks import generate_token as gen_webhook_token
from app.models.audit import AuditLog
from app.models.integration import ApiKey, ConnectorInstance, DatabaseConnection, ScheduledJob, WebhookEndpoint
from app.models.usage import UsageMetric
from app.models.user import RoleEnum, User
from app.schemas.integrations import (
    ApiKeyCreate,
    ApiKeyCreated,
    ApiKeyOut,
    AuditLogOut,
    ConnectorCatalogEntry,
    ConnectorCreate,
    ConnectorOut,
    DatabaseConnectionCreate,
    DatabaseConnectionOut,
    PushRequest,
    ScheduledJobCreate,
    ScheduledJobOut,
    ScheduledJobUpdate,
    UsageMetricOut,
    WebhookCreate,
    WebhookCreated,
    WebhookOut,
)
from app.services import connectors, db_connector, integration_pipeline

router = APIRouter(prefix="/api/integrations", tags=["integrations"])

INGESTABLE_MODULES = set(integration_pipeline.MODULE_SCHEMAS.keys())


def _validate_module(module_key: str) -> None:
    if module_key not in INGESTABLE_MODULES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"module_key must be one of {sorted(INGESTABLE_MODULES)}")


# ---------------------------------------------------------------- API keys (#3, #6 auth)
@router.post("/api-keys", response_model=ApiKeyCreated, status_code=status.HTTP_201_CREATED)
def create_api_key(
    payload: ApiKeyCreate,
    org_id: int = Depends(current_org_id),
    user: User = Depends(require_roles(RoleEnum.org_admin, RoleEnum.super_admin)),
    db: Session = Depends(get_db),
):
    raw_key = f"eak_{secrets.token_urlsafe(32)}"
    key = ApiKey(organization_id=org_id, name=payload.name, key_prefix=raw_key[:12], key_hash=hash_api_key(raw_key))
    db.add(key)
    db.commit()
    db.refresh(key)
    log_action(db, org_id, user.id, "api_key.created", {"name": payload.name, "key_id": key.id})
    return ApiKeyCreated(id=key.id, name=key.name, key_prefix=key.key_prefix, raw_key=raw_key)


@router.get("/api-keys", response_model=list[ApiKeyOut])
def list_api_keys(org_id: int = Depends(current_org_id), db: Session = Depends(get_db)):
    return db.query(ApiKey).filter(ApiKey.organization_id == org_id).all()


@router.delete("/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_api_key(
    key_id: int,
    org_id: int = Depends(current_org_id),
    user: User = Depends(require_roles(RoleEnum.org_admin, RoleEnum.super_admin)),
    db: Session = Depends(get_db),
):
    key = db.query(ApiKey).filter(ApiKey.id == key_id, ApiKey.organization_id == org_id).first()
    if key is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "API key not found")
    key.revoked = True
    db.commit()
    log_action(db, org_id, user.id, "api_key.revoked", {"key_id": key_id})


# ---------------------------------------------------------------- Database connector (#2)
@router.post("/db-connections", response_model=DatabaseConnectionOut, status_code=status.HTTP_201_CREATED)
def create_db_connection(
    payload: DatabaseConnectionCreate,
    org_id: int = Depends(current_org_id),
    user: User = Depends(require_roles(RoleEnum.org_admin, RoleEnum.super_admin)),
    db: Session = Depends(get_db),
):
    _validate_module(payload.module_key)
    conn = DatabaseConnection(
        organization_id=org_id,
        module_key=payload.module_key,
        name=payload.name,
        dialect=payload.dialect,
        host=payload.host,
        port=payload.port,
        database_name=payload.database_name,
        username=payload.username,
        encrypted_password=encrypt_secret(payload.password),
        source_query=payload.source_query,
    )
    db.add(conn)
    db.commit()
    db.refresh(conn)
    log_action(db, org_id, user.id, "db_connection.created", {"name": payload.name, "module_key": payload.module_key})
    return conn


@router.get("/db-connections", response_model=list[DatabaseConnectionOut])
def list_db_connections(org_id: int = Depends(current_org_id), db: Session = Depends(get_db)):
    return db.query(DatabaseConnection).filter(DatabaseConnection.organization_id == org_id).all()


@router.delete("/db-connections/{conn_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_db_connection(
    conn_id: int,
    org_id: int = Depends(current_org_id),
    user: User = Depends(require_roles(RoleEnum.org_admin, RoleEnum.super_admin)),
    db: Session = Depends(get_db),
):
    conn = db.query(DatabaseConnection).filter(DatabaseConnection.id == conn_id, DatabaseConnection.organization_id == org_id).first()
    if conn is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Connection not found")
    db.delete(conn)
    db.commit()
    log_action(db, org_id, user.id, "db_connection.deleted", {"conn_id": conn_id})


@router.post("/db-connections/{conn_id}/test")
def test_db_connection(conn_id: int, org_id: int = Depends(current_org_id), db: Session = Depends(get_db)):
    conn = db.query(DatabaseConnection).filter(DatabaseConnection.id == conn_id, DatabaseConnection.organization_id == org_id).first()
    if conn is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Connection not found")
    return db_connector.test_connection(conn)


@router.post("/db-connections/{conn_id}/sync")
def sync_db_connection(
    conn_id: int,
    org_id: int = Depends(current_org_id),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conn = db.query(DatabaseConnection).filter(DatabaseConnection.id == conn_id, DatabaseConnection.organization_id == org_id).first()
    if conn is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Connection not found")
    try:
        df = db_connector.fetch_rows(conn)
        result = integration_pipeline.auto_ingest(db, org_id, conn.module_key, df)
    except Exception as exc:
        conn.last_status = f"failed: {exc}"
        db.commit()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Sync failed: {exc}") from exc

    from app.models.base import utcnow

    conn.last_synced_at = utcnow()
    conn.last_status = f"ok: {result}"
    db.commit()
    log_action(db, org_id, user.id, "db_connection.synced", {"conn_id": conn_id, "result": result})
    return result


# ---------------------------------------------------------------- Scheduled sync / retrain (#4)
@router.post("/scheduled-jobs", response_model=ScheduledJobOut, status_code=status.HTTP_201_CREATED)
def create_scheduled_job(
    payload: ScheduledJobCreate,
    org_id: int = Depends(current_org_id),
    user: User = Depends(require_roles(RoleEnum.org_admin, RoleEnum.super_admin)),
    db: Session = Depends(get_db),
):
    if payload.job_type not in ("data_sync", "retrain"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "job_type must be 'data_sync' or 'retrain'")
    if payload.job_type == "data_sync" and payload.connection_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "connection_id is required for job_type 'data_sync'")
    job = ScheduledJob(
        organization_id=org_id, module_key=payload.module_key, job_type=payload.job_type,
        connection_id=payload.connection_id, interval_minutes=payload.interval_minutes,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    log_action(db, org_id, user.id, "scheduled_job.created", {"job_id": job.id, "job_type": payload.job_type})
    return job


@router.get("/scheduled-jobs", response_model=list[ScheduledJobOut])
def list_scheduled_jobs(org_id: int = Depends(current_org_id), db: Session = Depends(get_db)):
    return db.query(ScheduledJob).filter(ScheduledJob.organization_id == org_id).all()


@router.put("/scheduled-jobs/{job_id}", response_model=ScheduledJobOut)
def update_scheduled_job(
    job_id: int,
    payload: ScheduledJobUpdate,
    org_id: int = Depends(current_org_id),
    user: User = Depends(require_roles(RoleEnum.org_admin, RoleEnum.super_admin)),
    db: Session = Depends(get_db),
):
    job = db.query(ScheduledJob).filter(ScheduledJob.id == job_id, ScheduledJob.organization_id == org_id).first()
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Scheduled job not found")
    if payload.enabled is not None:
        job.enabled = payload.enabled
    if payload.interval_minutes is not None:
        job.interval_minutes = payload.interval_minutes
    db.commit()
    db.refresh(job)
    log_action(db, org_id, user.id, "scheduled_job.updated", {"job_id": job_id, **payload.model_dump(exclude_none=True)})
    return job


@router.delete("/scheduled-jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_scheduled_job(
    job_id: int,
    org_id: int = Depends(current_org_id),
    user: User = Depends(require_roles(RoleEnum.org_admin, RoleEnum.super_admin)),
    db: Session = Depends(get_db),
):
    job = db.query(ScheduledJob).filter(ScheduledJob.id == job_id, ScheduledJob.organization_id == org_id).first()
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Scheduled job not found")
    db.delete(job)
    db.commit()
    log_action(db, org_id, user.id, "scheduled_job.deleted", {"job_id": job_id})


# ---------------------------------------------------------------- Webhooks (#5)
@router.post("/webhooks", response_model=WebhookCreated, status_code=status.HTTP_201_CREATED)
def create_webhook(
    payload: WebhookCreate,
    org_id: int = Depends(current_org_id),
    user: User = Depends(require_roles(RoleEnum.org_admin, RoleEnum.super_admin)),
    db: Session = Depends(get_db),
):
    _validate_module(payload.module_key)
    token = gen_webhook_token()
    secret = gen_webhook_secret()
    webhook = WebhookEndpoint(
        organization_id=org_id, module_key=payload.module_key, token=token, encrypted_secret=encrypt_secret(secret)
    )
    db.add(webhook)
    db.commit()
    db.refresh(webhook)
    log_action(db, org_id, user.id, "webhook.created", {"webhook_id": webhook.id, "module_key": payload.module_key})
    return WebhookCreated(id=webhook.id, module_key=webhook.module_key, url_path=f"/api/webhooks/{token}", secret=secret)


@router.get("/webhooks", response_model=list[WebhookOut])
def list_webhooks(org_id: int = Depends(current_org_id), db: Session = Depends(get_db)):
    return db.query(WebhookEndpoint).filter(WebhookEndpoint.organization_id == org_id).all()


@router.delete("/webhooks/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_webhook(
    webhook_id: int,
    org_id: int = Depends(current_org_id),
    user: User = Depends(require_roles(RoleEnum.org_admin, RoleEnum.super_admin)),
    db: Session = Depends(get_db),
):
    webhook = db.query(WebhookEndpoint).filter(WebhookEndpoint.id == webhook_id, WebhookEndpoint.organization_id == org_id).first()
    if webhook is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Webhook not found")
    db.delete(webhook)
    db.commit()
    log_action(db, org_id, user.id, "webhook.deleted", {"webhook_id": webhook_id})


# ---------------------------------------------------------------- Pre-built connectors (#6)
@router.get("/connectors/catalog", response_model=list[ConnectorCatalogEntry])
def connector_catalog():
    return connectors.CATALOG


@router.post("/connectors", response_model=ConnectorOut, status_code=status.HTTP_201_CREATED)
def create_connector(
    payload: ConnectorCreate,
    org_id: int = Depends(current_org_id),
    user: User = Depends(require_roles(RoleEnum.org_admin, RoleEnum.super_admin)),
    db: Session = Depends(get_db),
):
    _validate_module(payload.module_key)
    catalog_entry = next((c for c in connectors.CATALOG if c["connector_type"] == payload.connector_type), None)
    if catalog_entry is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unknown connector_type '{payload.connector_type}'")

    instance = ConnectorInstance(
        organization_id=org_id, connector_type=payload.connector_type, module_key=payload.module_key,
        name=payload.name, status=catalog_entry["status"],
    )
    db.add(instance)
    db.commit()
    db.refresh(instance)
    log_action(db, org_id, user.id, "connector.created", {"connector_id": instance.id, "connector_type": payload.connector_type})
    return instance


@router.get("/connectors", response_model=list[ConnectorOut])
def list_connectors(org_id: int = Depends(current_org_id), db: Session = Depends(get_db)):
    return db.query(ConnectorInstance).filter(ConnectorInstance.organization_id == org_id).all()


@router.post("/connectors/{connector_id}/sync")
def sync_connector(
    connector_id: int,
    org_id: int = Depends(current_org_id),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    instance = db.query(ConnectorInstance).filter(ConnectorInstance.id == connector_id, ConnectorInstance.organization_id == org_id).first()
    if instance is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Connector not found")
    if instance.connector_type == "generic_rest":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "generic_rest has no simulator — push data via POST /api/integrations/push/{module_key} instead")

    df = connectors.generate_sample_batch(instance.connector_type, instance.module_key)
    result = integration_pipeline.auto_ingest(db, org_id, instance.module_key, df)

    from app.models.base import utcnow

    instance.last_synced_at = utcnow()
    db.commit()
    log_action(db, org_id, user.id, "connector.synced", {"connector_id": connector_id, "result": result})
    return {**result, "status": instance.status}


@router.delete("/connectors/{connector_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_connector(
    connector_id: int,
    org_id: int = Depends(current_org_id),
    user: User = Depends(require_roles(RoleEnum.org_admin, RoleEnum.super_admin)),
    db: Session = Depends(get_db),
):
    instance = db.query(ConnectorInstance).filter(ConnectorInstance.id == connector_id, ConnectorInstance.organization_id == org_id).first()
    if instance is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Connector not found")
    db.delete(instance)
    db.commit()
    log_action(db, org_id, user.id, "connector.deleted", {"connector_id": connector_id})


# ---------------------------------------------------------------- REST API push (#3)
@router.post("/push/{module_key}")
def push_records(
    module_key: str,
    payload: PushRequest,
    org_id: int = Depends(org_id_from_api_key),
    db: Session = Depends(get_db),
):
    _validate_module(module_key)
    if not payload.records:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "records must be a non-empty list")
    df = pd.DataFrame(payload.records)
    try:
        result = integration_pipeline.auto_ingest(db, org_id, module_key, df)
    except (ValueError, KeyError) as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return result


# ---------------------------------------------------------------- Observability
@router.get("/audit-log", response_model=list[AuditLogOut])
def get_audit_log(
    limit: int = 50,
    org_id: int = Depends(current_org_id),
    _user: User = Depends(require_roles(RoleEnum.org_admin, RoleEnum.super_admin)),
    db: Session = Depends(get_db),
):
    return (
        db.query(AuditLog)
        .filter(AuditLog.organization_id == org_id)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
        .all()
    )


@router.get("/usage", response_model=list[UsageMetricOut])
def get_usage(
    days: int = 14,
    org_id: int = Depends(current_org_id),
    _user: User = Depends(require_roles(RoleEnum.org_admin, RoleEnum.super_admin)),
    db: Session = Depends(get_db),
):
    from datetime import timedelta

    from app.models.base import utcnow

    since = (utcnow() - timedelta(days=days)).date()
    rows = (
        db.query(UsageMetric)
        .filter(UsageMetric.organization_id == org_id, UsageMetric.day >= since)
        .order_by(UsageMetric.day.desc())
        .all()
    )
    return [UsageMetricOut(module_key=r.module_key, day=r.day.isoformat(), request_count=r.request_count) for r in rows]
