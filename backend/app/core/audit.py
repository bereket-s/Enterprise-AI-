from sqlalchemy.orm import Session

from app.models.audit import AuditLog


def log_action(db: Session, org_id: int, user_id: int | None, action: str, detail: dict | None = None) -> None:
    db.add(AuditLog(organization_id=org_id, user_id=user_id, action=action, detail=detail or {}))
    db.commit()
