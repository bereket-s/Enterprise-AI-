"""Public inbound webhook receiver (#5). Deliberately outside app/api/integrations.py
and not behind get_current_user or org_id_from_api_key — a webhook sender is the
company's own backend system firing an event in real time, not a logged-in user or
a holder of our API key, so it authenticates itself by signing the raw request body
with the secret it was given when the endpoint was created (app/core/webhooks.py).
"""
from __future__ import annotations

import json

import pandas as pd
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.crypto import decrypt_secret
from app.core.database import get_db
from app.core.webhooks import verify as verify_signature
from app.models.base import utcnow
from app.models.integration import WebhookEndpoint
from app.services import integration_pipeline

router = APIRouter(prefix="/api/webhooks", tags=["webhooks-public"])


@router.post("/{token}")
async def receive_webhook(
    token: str,
    request: Request,
    x_signature: str = Header(..., alias="X-Signature"),
    db: Session = Depends(get_db),
):
    webhook = db.query(WebhookEndpoint).filter(WebhookEndpoint.token == token).first()
    if webhook is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown webhook endpoint")

    body = await request.body()
    secret = decrypt_secret(webhook.encrypted_secret)
    if not verify_signature(body, secret, x_signature):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid signature")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Body must be valid JSON") from exc
    if isinstance(payload, dict):
        payload = [payload]
    if not isinstance(payload, list) or not payload:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Body must be a JSON object or a non-empty array of objects")

    df = pd.DataFrame(payload)
    try:
        result = integration_pipeline.auto_ingest(db, webhook.organization_id, webhook.module_key, df)
    except (ValueError, KeyError) as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    webhook.last_received_at = utcnow()
    webhook.receive_count += len(payload)
    db.commit()
    return {"received": len(payload), "result": result}
