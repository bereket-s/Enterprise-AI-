import hashlib

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.base import utcnow
from app.models.integration import ApiKey
from app.models.organization import ModuleEnablement
from app.models.user import RoleEnum, User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None or "sub" not in payload:
        raise credentials_error
    user = db.get(User, int(payload["sub"]))
    if user is None or not user.is_active:
        raise credentials_error
    return user


def require_roles(*roles: RoleEnum):
    def _check(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role.value}' is not permitted to perform this action",
            )
        return user

    return _check


def current_org_id(user: User = Depends(get_current_user)) -> int:
    """Every tenant-scoped endpoint depends on this instead of trusting a client-supplied org id.

    This is the single choke point that enforces multi-tenant isolation: a request's
    organization scope always comes from the authenticated user's token, never from
    a path/query parameter, so Company A can never read Company B's data by guessing IDs.
    """
    if user.organization_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not attached to an organization",
        )
    return user.organization_id


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


def org_id_from_api_key(x_api_key: str = Header(...), db: Session = Depends(get_db)) -> int:
    """Resolves the tenant from a machine-to-machine API key (header X-API-Key)
    instead of a user's JWT — used by the REST-push (#3), webhook (#5), and
    connector (#6) integration paths, none of which have a logged-in human.
    """
    key_hash = hash_api_key(x_api_key)
    key = db.query(ApiKey).filter(ApiKey.key_hash == key_hash, ApiKey.revoked.is_(False)).first()
    if key is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or revoked API key")
    key.last_used_at = utcnow()
    db.commit()
    return key.organization_id


def _assert_module_enabled(db: Session, org_id: int, module_key: str) -> None:
    enablement = (
        db.query(ModuleEnablement)
        .filter(ModuleEnablement.organization_id == org_id, ModuleEnablement.module_key == module_key)
        .first()
    )
    if enablement is None or not enablement.enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Module '{module_key}' is not enabled for this organization",
        )


def require_module_enabled(module_key: str):
    """Gate a module's router behind that org's module toggle (JWT-authenticated routes).

    A disabled module returns 403 even for an org_admin — enabling it via
    PUT /api/org/modules/{key} is the only way back in, which is what makes
    "companies choose which features they want" an enforced rule rather than
    just a UI convention.
    """

    def _check(org_id: int = Depends(current_org_id), db: Session = Depends(get_db)) -> int:
        _assert_module_enabled(db, org_id, module_key)
        return org_id

    return _check


def require_module_enabled_api_key(module_key: str):
    """Same module-toggle enforcement as require_module_enabled, but for
    API-key-authenticated integration endpoints instead of a logged-in user."""

    def _check(org_id: int = Depends(org_id_from_api_key), db: Session = Depends(get_db)) -> int:
        _assert_module_enabled(db, org_id, module_key)
        return org_id

    return _check
