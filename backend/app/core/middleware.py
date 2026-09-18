"""Structured request logging + per-tenant usage counters — the "observability"
gap from docs/architecture.md §10 (structured logging, request tracing, and
per-tenant usage metrics for billing).
"""
from __future__ import annotations

import json
import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger("request")
logging.basicConfig(level=logging.INFO)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 1)

        response.headers["X-Request-ID"] = request_id
        logger.info(
            json.dumps(
                {
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "duration_ms": duration_ms,
                }
            )
        )
        _record_usage(request, response)
        return response


def _module_key_from_path(path: str) -> str | None:
    parts = [p for p in path.split("/") if p]
    if len(parts) >= 2 and parts[0] == "api":
        return parts[1]
    return None


def _record_usage(request: Request, response) -> None:
    """Best-effort: never let usage bookkeeping fail a real request."""
    if response.status_code >= 500:
        return
    try:
        from app.core.database import SessionLocal
        from app.core.security import decode_access_token
        from app.models.base import utcnow
        from app.models.usage import UsageMetric
        from app.models.user import User

        auth_header = request.headers.get("authorization", "")
        org_id = None
        if auth_header.lower().startswith("bearer "):
            payload = decode_access_token(auth_header[7:])
            if payload and "sub" in payload:
                db = SessionLocal()
                try:
                    user = db.get(User, int(payload["sub"]))
                    org_id = user.organization_id if user else None
                finally:
                    db.close()
        if org_id is None:
            return

        module_key = _module_key_from_path(request.url.path) or "other"
        today = utcnow().date()
        db = SessionLocal()
        try:
            row = (
                db.query(UsageMetric)
                .filter(UsageMetric.organization_id == org_id, UsageMetric.module_key == module_key, UsageMetric.day == today)
                .first()
            )
            if row is None:
                row = UsageMetric(organization_id=org_id, module_key=module_key, day=today, request_count=0)
                db.add(row)
            row.request_count += 1
            db.commit()
        finally:
            db.close()
    except Exception:  # noqa: BLE001 - usage tracking must never break a request
        logger.exception("Usage metric recording failed")
