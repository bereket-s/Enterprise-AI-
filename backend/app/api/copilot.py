from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import current_org_id, get_current_user
from app.models.copilot import ChatLog
from app.models.user import User
from app.schemas.copilot import AskRequest, ChatLogOut
from app.services import copilot_service

router = APIRouter(prefix="/api/copilot", tags=["ai-copilot"])


@router.post("/ask", response_model=ChatLogOut)
def ask(
    payload: AskRequest,
    org_id: int = Depends(current_org_id),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return copilot_service.ask(db, org_id, user.id, payload.question)


@router.get("/history", response_model=list[ChatLogOut])
def history(limit: int = 20, org_id: int = Depends(current_org_id), db: Session = Depends(get_db)):
    return (
        db.query(ChatLog)
        .filter(ChatLog.organization_id == org_id)
        .order_by(ChatLog.created_at.desc())
        .limit(limit)
        .all()
    )
