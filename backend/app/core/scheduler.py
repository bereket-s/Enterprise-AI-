"""Drives scheduled data syncs (#4) and scheduled model retraining — the
"scheduled retraining" half of the model-registry gap in docs/architecture.md
§10. A single repeating tick (every 60s) scans ScheduledJob rows in the database
rather than registering one APScheduler job per row, so schedules survive a
process restart with no extra bookkeeping: the "due" calculation is derived from
`last_run_at` + `interval_minutes`, both persisted in the database, not from
APScheduler's own in-memory job store.
"""
from __future__ import annotations

import logging
from datetime import timedelta

from apscheduler.schedulers.background import BackgroundScheduler

from app.core.database import SessionLocal
from app.models.base import utcnow
from app.models.integration import DatabaseConnection, ScheduledJob

logger = logging.getLogger("scheduler")

_scheduler: BackgroundScheduler | None = None
TICK_SECONDS = 60


def _run_data_sync(db, job: ScheduledJob) -> str:
    from app.services import db_connector, integration_pipeline

    connection = db.get(DatabaseConnection, job.connection_id)
    if connection is None:
        return "failed: database connection was deleted"
    df = db_connector.fetch_rows(connection)
    result = integration_pipeline.auto_ingest(db, job.organization_id, job.module_key, df)
    connection.last_synced_at = utcnow()
    connection.last_status = f"ok: {result}"
    db.commit()
    return f"ok: {result}"


def _run_retrain(db, job: ScheduledJob) -> str:
    from app.services import fraud_service, maintenance_service, workforce_service

    trainers = {
        "fraud": fraud_service.train_and_score,
        "maintenance": maintenance_service.train_and_score,
        "workforce": workforce_service.train_attrition_and_score,
    }
    trainer = trainers.get(job.module_key)
    if trainer is None:
        return f"failed: no trainer registered for module '{job.module_key}'"
    evaluation = trainer(db, job.organization_id)
    return f"ok: version trained, metrics={evaluation.metrics.get('roc_auc')}"


def _tick() -> None:
    db = SessionLocal()
    try:
        due_jobs = db.query(ScheduledJob).filter(ScheduledJob.enabled.is_(True)).all()
        now = utcnow()
        for job in due_jobs:
            due = job.last_run_at is None or (now - job.last_run_at) >= timedelta(minutes=job.interval_minutes)
            if not due:
                continue
            try:
                status = _run_data_sync(db, job) if job.job_type == "data_sync" else _run_retrain(db, job)
            except Exception as exc:  # noqa: BLE001 - a failing scheduled job must not crash the scheduler
                status = f"failed: {exc}"
                logger.exception("Scheduled job %s failed", job.id)
            job.last_run_at = now
            job.last_status = status[:500]
            db.commit()
    finally:
        db.close()


def start_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is not None:
        return _scheduler
    _scheduler = BackgroundScheduler()
    _scheduler.add_job(_tick, "interval", seconds=TICK_SECONDS, id="scheduled_jobs_tick", max_instances=1)
    _scheduler.start()
    return _scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None


def run_tick_now() -> None:
    """Exposed for tests / a manual 'run due jobs now' admin action, instead of
    waiting up to TICK_SECONDS for the background tick."""
    _tick()
